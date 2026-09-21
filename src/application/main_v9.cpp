// `protocol-application-v9`: a version-nine ledger, application, clock, and
// socket in one process.
//
// It is version eight's `main_v8.cpp` with the version rebound, the genesis
// width read from `v9::kGenesisPrefixBytes` — 150 octets, because version nine's
// genesis gains a timestamp — and **one thing version eight never had: a clock.**
//
// **The clock is the platform real-time clock, and it is bound here and nowhere
// else.** `ApplicationV9` reads it once per `ProcessProposal` and on no other
// path, so this file decides only where the reading comes from and what happens
// when there is none. `consensus-application-v2` answers the second: a
// deployment that cannot read a clock cannot vote on a proposal and must fail to
// start rather than vote on an assumed value. So the clock is read once before
// anything is opened, and a process whose clock stops being readable later stops
// too — it does not substitute a value, because every substitute makes C5 pass
// or fail on something other than the time.
//
// **Genesis validity reads no clock.** A genesis whose stamp is outside
// `calendar-v1`'s range is refused by `decode_genesis`; one inside it is
// well-formed whatever this machine's clock says, because the chain identity is
// a hash of the genesis bytes and a clock-dependent validity rule would give two
// machines different identities for one chain.

#include "protocol/application/application_v9.hpp"
#include "protocol/application/unix_server_v1.hpp"
#include "protocol/storage/sqlite_ledger_v9.hpp"
#include "protocol/v9/economy.hpp"
#include "protocol/v9/ledger.hpp"

#include <csignal>
#include <cstdint>
#include <ctime>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <span>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <sys/signalfd.h>
#include <unistd.h>
#include <utility>
#include <variant>

namespace pa = protocol::application;
namespace ps = protocol::storage;
namespace v9 = protocol::v9;

namespace {

class SignalDescriptor {
 public:
  explicit SignalDescriptor(int value) noexcept : value_(value) {}
  ~SignalDescriptor() noexcept {
    if (value_ >= 0) (void)::close(value_);
  }

  SignalDescriptor(const SignalDescriptor&) = delete;
  SignalDescriptor& operator=(const SignalDescriptor&) = delete;

  int get() const noexcept { return value_; }

 private:
  int value_;
};

int make_signal_descriptor() noexcept {
  sigset_t signals{};
  if (::sigemptyset(&signals) != 0 || ::sigaddset(&signals, SIGINT) != 0 ||
      ::sigaddset(&signals, SIGTERM) != 0 ||
      ::sigprocmask(SIG_BLOCK, &signals, nullptr) != 0) {
    return -1;
  }
  return ::signalfd(-1, &signals, SFD_CLOEXEC | SFD_NONBLOCK);
}

int fail(std::string_view message) {
  std::cerr << "protocol-application-v9: " << message << '\n';
  return 1;
}

// Milliseconds since `calendar-v1`'s `TIMESTAMP_EPOCH`, which is the Unix epoch,
// truncated toward zero exactly as the contract converts a block stamp. A
// reading before the epoch is not a reading: no `u64` millisecond count
// represents it.
std::optional<std::uint64_t> read_realtime_millis() noexcept {
  timespec now{};
  if (::clock_gettime(CLOCK_REALTIME, &now) != 0 || now.tv_sec < 0 ||
      now.tv_nsec < 0 || now.tv_nsec > 999'999'999) {
    return std::nullopt;
  }
  const auto seconds = static_cast<std::uint64_t>(now.tv_sec);
  if (seconds > (std::numeric_limits<std::uint64_t>::max() - 999U) / 1000U) {
    return std::nullopt;
  }
  return seconds * 1000U + static_cast<std::uint64_t>(now.tv_nsec) / 1'000'000U;
}

// Raised from inside `ProcessProposal` when the clock stops being readable. It
// unwinds out of the serve loop to `main`, which reports it and exits nonzero;
// the socket and the store close on the way. Nothing was staged or written by
// the time the clock is read, so there is nothing to undo.
class ClockUnreadable : public std::runtime_error {
 public:
  ClockUnreadable()
      : std::runtime_error("the platform real-time clock became unreadable") {}
};

pa::ClockSourceV9 realtime_clock() {
  return []() -> std::uint64_t {
    const auto now = read_realtime_millis();
    if (!now) throw ClockUnreadable();
    return *now;
  };
}

// The size check is an **allocation bound**, not a validity rule: a
// version-nine genesis is exactly `kGenesisPrefixBytes` octets, so nothing
// larger is read into memory. The validity rule — including C1 on the genesis
// stamp — is stated once, in the kernel, and `decode_genesis` refuses any file
// its encoder would not have produced.
std::variant<v9::Genesis, std::string_view> read_genesis(
    const std::filesystem::path& path) {
  std::error_code error;
  if (!path.is_absolute() || !std::filesystem::is_regular_file(path, error) ||
      error) {
    return std::string_view{"genesis path is not an absolute regular file"};
  }
  const auto size = std::filesystem::file_size(path, error);
  if (error || size != v9::kGenesisPrefixBytes) {
    return std::string_view{
        "genesis file is not the canonical version-nine width"};
  }
  v9::Bytes bytes(static_cast<std::size_t>(size));
  std::ifstream input(path, std::ios::binary);
  if (!input || !input.read(reinterpret_cast<char*>(bytes.data()),
                            static_cast<std::streamsize>(size))) {
    return std::string_view{"failed to read the exact genesis file"};
  }
  auto genesis = v9::decode_genesis(bytes);
  if (!genesis) {
    return std::string_view{
        "genesis file is not a canonical version-nine genesis"};
  }
  return *genesis;
}

// An absent database is created; anything else is opened and validated. Asking
// to open first is what makes a restart ordinary rather than a special case.
ps::SQLiteLedgerV9Result open_or_create_ledger(
    const std::filesystem::path& path, const v9::Genesis& genesis) {
  auto opened = ps::open_sqlite_ledger_v9(path, genesis);
  if (!std::holds_alternative<ps::SQLiteLedgerV9Error>(opened.result) ||
      std::get<ps::SQLiteLedgerV9Error>(opened.result) !=
          ps::SQLiteLedgerV9Error::path_not_found) {
    return opened;
  }
  return ps::create_sqlite_ledger_v9(path, genesis);
}

template <typename Hash>
std::string uppercase_hex(const Hash& value) {
  std::ostringstream output;
  output << std::hex << std::uppercase << std::setfill('0');
  for (const auto byte : value) {
    output << std::setw(2) << static_cast<unsigned>(byte);
  }
  return output.str();
}

// The figures an operator has to put into a consensus engine's configuration,
// printed without touching a database or a clock. **Version nine adds the
// genesis stamp**, in decimal milliseconds, because CometBFT's genesis gains a
// fifth derived value, `genesis_time`, and the launcher must derive it from the
// same validated canonical genesis as the other four. Rendering it as a civil
// time is the launcher's job; this prints the value the chain commits to.
int print_genesis_identity(const std::filesystem::path& genesis_path) {
  auto genesis = read_genesis(genesis_path);
  if (!std::holds_alternative<v9::Genesis>(genesis)) {
    return fail(std::get<std::string_view>(genesis));
  }
  const auto& value = std::get<v9::Genesis>(genesis);
  const auto identity = v9::chain_id(value);
  auto opened = v9::open_ledger(value);
  if (!identity || !opened) return fail("failed to validate canonical genesis");
  const auto root = v9::ledger_state_root(*opened);
  if (!root) return fail("failed to derive the height-zero state root");
  std::cout << "chain_id=" << uppercase_hex(*identity) << '\n'
            << "app_hash=" << uppercase_hex(*root) << '\n'
            << "genesis_timestamp=" << value.genesis_timestamp << '\n';
  return 0;
}

int serve(pa::ApplicationV9& app, pa::UnixSocketServerV1& listener,
          int shutdown) {
  for (;;) {
    const auto served = listener.serve_connection(app, shutdown);
    if (std::holds_alternative<std::monostate>(served)) continue;
    const auto error = std::get<pa::UnixServerError>(served);
    if (error == pa::UnixServerError::shutdown_requested) return 0;
    // A peer that hangs up badly or speaks nonsense — including a version-one
    // frame, which this socket refuses at the header — loses its connection and
    // nothing else. The application's own terminal latch is what stops a node
    // that has contradicted itself, and it is not this loop's business.
    if (error == pa::UnixServerError::connection_failure ||
        error == pa::UnixServerError::protocol_failure) {
      continue;
    }
    return fail("Unix socket listener failed");
  }
}

int run_application(int argc, char** argv) {
  if (argc == 3 && std::string_view(argv[1]) == "--genesis-identity") {
    return print_genesis_identity(std::filesystem::path(argv[2]));
  }
  if (argc != 4) {
    return fail(
        "usage: protocol-application-v9 <absolute-database> "
        "<absolute-genesis> <absolute-socket> | "
        "protocol-application-v9 --genesis-identity <absolute-genesis>");
  }
  const std::filesystem::path database_path(argv[1]);
  const std::filesystem::path genesis_path(argv[2]);
  const std::filesystem::path socket_path(argv[3]);
  if (!database_path.is_absolute() || !socket_path.is_absolute()) {
    return fail("database and socket paths must be absolute");
  }
  // **Before anything is opened.** A machine that cannot read a clock must not
  // come up far enough to be asked for a vote.
  if (!read_realtime_millis()) {
    return fail("the platform real-time clock cannot be read");
  }
  SignalDescriptor shutdown(make_signal_descriptor());
  if (shutdown.get() < 0) {
    return fail("failed to create the shutdown signal descriptor");
  }

  auto genesis = read_genesis(genesis_path);
  if (!std::holds_alternative<v9::Genesis>(genesis)) {
    return fail(std::get<std::string_view>(genesis));
  }
  auto ledger =
      open_or_create_ledger(database_path, std::get<v9::Genesis>(genesis));
  if (!std::holds_alternative<ps::SQLiteLedgerV9>(ledger.result)) {
    return fail("failed to create or validate the SQLite ledger");
  }
  auto application = pa::make_application_v9(
      std::get<ps::SQLiteLedgerV9>(std::move(ledger.result)), realtime_clock());
  if (!std::holds_alternative<pa::ApplicationV9>(application.result)) {
    return fail("failed to initialize the application lifecycle");
  }
  auto server = pa::make_unix_socket_server_v1(socket_path);
  if (!std::holds_alternative<pa::UnixSocketServerV1>(server.result)) {
    return fail("failed to create the private Unix socket");
  }

  auto app = std::get<pa::ApplicationV9>(std::move(application.result));
  auto listener = std::get<pa::UnixSocketServerV1>(std::move(server.result));
  return serve(app, listener, shutdown.get());
}

}  // namespace

int main(int argc, char** argv) {
  try {
    return run_application(argc, argv);
  } catch (const ClockUnreadable& error) {
    return fail(std::string(error.what()) +
                "; stopping rather than voting on an assumed value");
  } catch (const std::exception&) {
    return fail("unhandled runtime failure");
  } catch (...) {
    return fail("unhandled non-standard failure");
  }
}

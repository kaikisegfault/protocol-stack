// `protocol-application-v7`: a version-seven ledger, application, and socket in
// one process.
//
// It is version one's `main.cpp` with three substitutions, and the third is the
// only interesting one. Version one hands its store the genesis **bytes**;
// version seven's store takes a `Genesis` **struct**, so this reads the
// canonical file and decodes it, and the store re-encodes what it was given and
// stores those octets. A file that would not have been produced by
// `encode_genesis` is refused here rather than becoming a chain nobody else can
// join.

#include "protocol/application/application_v7.hpp"
#include "protocol/application/unix_server_v1.hpp"
#include "protocol/storage/sqlite_ledger_v7.hpp"
#include "protocol/v7/economy.hpp"
#include "protocol/v7/ledger.hpp"

#include <csignal>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <span>
#include <sstream>
#include <string>
#include <string_view>
#include <sys/signalfd.h>
#include <unistd.h>
#include <utility>
#include <variant>

namespace pa = protocol::application;
namespace ps = protocol::storage;
namespace v7 = protocol::v7;

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
  std::cerr << "protocol-application-v7: " << message << '\n';
  return 1;
}

// The size check here is an **allocation bound**, not a validity rule: a
// version-seven genesis is exactly `kGenesisPrefixBytes` octets, so nothing
// larger is ever read into memory. The validity rule is stated once, in
// `decode_genesis`, and this function does not restate any part of it.
std::variant<v7::Genesis, std::string_view> read_genesis(
    const std::filesystem::path& path) {
  std::error_code error;
  if (!path.is_absolute() || !std::filesystem::is_regular_file(path, error) ||
      error) {
    return std::string_view{"genesis path is not an absolute regular file"};
  }
  const auto size = std::filesystem::file_size(path, error);
  if (error || size != v7::kGenesisPrefixBytes) {
    return std::string_view{"genesis file is not the canonical 110 octets"};
  }
  v7::Bytes bytes(static_cast<std::size_t>(size));
  std::ifstream input(path, std::ios::binary);
  if (!input || !input.read(reinterpret_cast<char*>(bytes.data()),
                            static_cast<std::streamsize>(size))) {
    return std::string_view{"failed to read the exact genesis file"};
  }
  auto genesis = v7::decode_genesis(bytes);
  if (!genesis) {
    return std::string_view{"genesis file is not a canonical version-seven genesis"};
  }
  return *genesis;
}

// An absent database is created; anything else is opened and validated. The
// order matters: a create over an existing path is refused by the store, so
// asking to open first is what makes a restart ordinary rather than a special
// case.
ps::SQLiteLedgerV7Result open_or_create_ledger(
    const std::filesystem::path& path, const v7::Genesis& genesis) {
  auto opened = ps::open_sqlite_ledger_v7(path, genesis);
  if (!std::holds_alternative<ps::SQLiteLedgerV7Error>(opened.result) ||
      std::get<ps::SQLiteLedgerV7Error>(opened.result) !=
          ps::SQLiteLedgerV7Error::path_not_found) {
    return opened;
  }
  return ps::create_sqlite_ledger_v7(path, genesis);
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

// The two figures an operator has to put into a consensus engine's
// configuration, printed without touching a database.
int print_genesis_identity(const std::filesystem::path& genesis_path) {
  auto genesis = read_genesis(genesis_path);
  if (!std::holds_alternative<v7::Genesis>(genesis)) {
    return fail(std::get<std::string_view>(genesis));
  }
  const auto& value = std::get<v7::Genesis>(genesis);
  const auto identity = v7::chain_id(value);
  auto opened = v7::open_ledger(value);
  if (!identity || !opened) return fail("failed to validate canonical genesis");
  const auto root = v7::ledger_state_root(*opened);
  if (!root) return fail("failed to derive the height-zero state root");
  std::cout << "chain_id=" << uppercase_hex(*identity) << '\n'
            << "app_hash=" << uppercase_hex(*root) << '\n';
  return 0;
}

int run_application(int argc, char** argv) {
  if (argc == 3 && std::string_view(argv[1]) == "--genesis-identity") {
    return print_genesis_identity(std::filesystem::path(argv[2]));
  }
  if (argc != 4) {
    return fail(
        "usage: protocol-application-v7 <absolute-database> "
        "<absolute-genesis> <absolute-socket> | "
        "protocol-application-v7 --genesis-identity <absolute-genesis>");
  }
  const std::filesystem::path database_path(argv[1]);
  const std::filesystem::path genesis_path(argv[2]);
  const std::filesystem::path socket_path(argv[3]);
  if (!database_path.is_absolute() || !socket_path.is_absolute()) {
    return fail("database and socket paths must be absolute");
  }
  SignalDescriptor shutdown(make_signal_descriptor());
  if (shutdown.get() < 0) {
    return fail("failed to create the shutdown signal descriptor");
  }

  auto genesis = read_genesis(genesis_path);
  if (!std::holds_alternative<v7::Genesis>(genesis)) {
    return fail(std::get<std::string_view>(genesis));
  }
  auto ledger =
      open_or_create_ledger(database_path, std::get<v7::Genesis>(genesis));
  if (!std::holds_alternative<ps::SQLiteLedgerV7>(ledger.result)) {
    return fail("failed to create or validate the SQLite ledger");
  }
  auto application = pa::make_application_v7(
      std::get<ps::SQLiteLedgerV7>(std::move(ledger.result)));
  if (!std::holds_alternative<pa::ApplicationV7>(application.result)) {
    return fail("failed to initialize the application lifecycle");
  }
  auto server = pa::make_unix_socket_server_v1(socket_path);
  if (!std::holds_alternative<pa::UnixSocketServerV1>(server.result)) {
    return fail("failed to create the private Unix socket");
  }

  auto app = std::get<pa::ApplicationV7>(std::move(application.result));
  auto listener = std::get<pa::UnixSocketServerV1>(std::move(server.result));
  for (;;) {
    const auto served = listener.serve_connection(app, shutdown.get());
    if (std::holds_alternative<std::monostate>(served)) continue;
    const auto error = std::get<pa::UnixServerError>(served);
    if (error == pa::UnixServerError::shutdown_requested) return 0;
    // A peer that hangs up badly or speaks nonsense loses its connection and
    // nothing else. The application's own terminal latch is what stops a node
    // that has contradicted itself, and it is not this loop's business.
    if (error == pa::UnixServerError::connection_failure ||
        error == pa::UnixServerError::protocol_failure) {
      continue;
    }
    return fail("Unix socket listener failed");
  }
}

}  // namespace

int main(int argc, char** argv) {
  try {
    return run_application(argc, argv);
  } catch (const std::exception&) {
    return fail("unhandled runtime failure");
  } catch (...) {
    return fail("unhandled non-standard failure");
  }
}

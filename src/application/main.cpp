#include "protocol/application/application_v1.hpp"
#include "protocol/application/unix_server_v1.hpp"
#include "protocol/storage/sqlite_ledger.hpp"

#include <csignal>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <span>
#include <string_view>
#include <sys/signalfd.h>
#include <unistd.h>
#include <utility>
#include <variant>

namespace pa = protocol::application;
namespace ps = protocol::storage;
namespace pv1 = protocol::v1;

namespace {

constexpr std::uintmax_t kMaximumGenesisBytes = 1'048'576;

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
  if (::sigemptyset(&signals) != 0 ||
      ::sigaddset(&signals, SIGINT) != 0 ||
      ::sigaddset(&signals, SIGTERM) != 0 ||
      ::sigprocmask(SIG_BLOCK, &signals, nullptr) != 0) {
    return -1;
  }
  return ::signalfd(-1, &signals, SFD_CLOEXEC | SFD_NONBLOCK);
}

std::variant<pv1::Bytes, std::string_view> read_genesis(
    const std::filesystem::path& path) {
  std::error_code error;
  if (!path.is_absolute() ||
      !std::filesystem::is_regular_file(path, error) || error) {
    return std::string_view{"genesis path is not an absolute regular file"};
  }
  const auto size = std::filesystem::file_size(path, error);
  if (error || size > kMaximumGenesisBytes) {
    return std::string_view{"genesis file is unavailable or too large"};
  }
  pv1::Bytes bytes(static_cast<std::size_t>(size));
  std::ifstream input(path, std::ios::binary);
  if (!input ||
      (size != 0 &&
       !input.read(
           reinterpret_cast<char*>(bytes.data()),
           static_cast<std::streamsize>(size)))) {
    return std::string_view{"failed to read the exact genesis file"};
  }
  return bytes;
}

ps::SQLiteLedgerResult open_or_create_ledger(
    const std::filesystem::path& path,
    std::span<const std::uint8_t> genesis) {
  auto opened = ps::open_sqlite_ledger(path, genesis);
  if (!std::holds_alternative<ps::SQLiteLedgerError>(opened.result) ||
      std::get<ps::SQLiteLedgerError>(opened.result) !=
          ps::SQLiteLedgerError::path_not_found) {
    return opened;
  }
  return ps::create_sqlite_ledger(path, genesis);
}

int fail(std::string_view message) {
  std::cerr << "protocol-application: " << message << '\n';
  return 1;
}

int run_application(int argc, char** argv) {
  if (argc != 4) {
    return fail(
        "usage: protocol-application "
        "<absolute-database> <absolute-genesis> <absolute-socket>");
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
  if (!std::holds_alternative<pv1::Bytes>(genesis)) {
    return fail(std::get<std::string_view>(genesis));
  }
  auto ledger = open_or_create_ledger(
      database_path, std::get<pv1::Bytes>(genesis));
  if (!std::holds_alternative<ps::SQLiteLedger>(ledger.result)) {
    return fail("failed to create or validate the SQLite ledger");
  }
  auto application = pa::make_application_v1(
      std::get<ps::SQLiteLedger>(std::move(ledger.result)));
  if (!std::holds_alternative<pa::ApplicationV1>(
          application.result)) {
    return fail("failed to initialize the application lifecycle");
  }
  auto server = pa::make_unix_socket_server_v1(socket_path);
  if (!std::holds_alternative<pa::UnixSocketServerV1>(
          server.result)) {
    return fail("failed to create the private Unix socket");
  }

  auto app =
      std::get<pa::ApplicationV1>(std::move(application.result));
  auto listener =
      std::get<pa::UnixSocketServerV1>(std::move(server.result));
  for (;;) {
    const auto served =
        listener.serve_connection(app, shutdown.get());
    if (std::holds_alternative<std::monostate>(served)) continue;
    const auto error = std::get<pa::UnixServerError>(served);
    if (error == pa::UnixServerError::shutdown_requested) return 0;
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

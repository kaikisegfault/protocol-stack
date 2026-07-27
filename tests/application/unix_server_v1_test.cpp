#include "protocol/application/unix_server_v1.hpp"
#include "protocol/application/wire_v1.hpp"
#include "protocol/storage/sqlite_ledger.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <cerrno>
#include <cstring>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <span>
#include <stdexcept>
#include <string_view>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <thread>
#include <unistd.h>
#include <utility>
#include <variant>

namespace pa = protocol::application;
namespace ps = protocol::storage;
namespace p = protocol::v1;
namespace pv = protocol_vectors;

namespace {

class TestFiles {
 public:
  explicit TestFiles(std::filesystem::path prefix)
      : database_(prefix.string() + ".db"),
        socket_(prefix.string() + ".sock"),
        second_socket_(prefix.string() + "-second.sock"),
        third_socket_(prefix.string() + "-third.sock"),
        occupied_(prefix.string() + "-occupied.sock") {
    remove();
  }
  ~TestFiles() { remove(); }

  const auto& database() const noexcept { return database_; }
  const auto& socket() const noexcept { return socket_; }
  const auto& second_socket() const noexcept {
    return second_socket_;
  }
  const auto& third_socket() const noexcept {
    return third_socket_;
  }
  const auto& occupied() const noexcept { return occupied_; }

 private:
  void remove() noexcept {
    std::error_code ignored;
    for (const auto& path :
         {database_, socket_, second_socket_, third_socket_, occupied_}) {
      std::filesystem::remove(path, ignored);
    }
    std::filesystem::remove(database_.string() + "-journal", ignored);
    std::filesystem::remove(database_.string() + "-wal", ignored);
    std::filesystem::remove(database_.string() + "-shm", ignored);
  }

  std::filesystem::path database_;
  std::filesystem::path socket_;
  std::filesystem::path second_socket_;
  std::filesystem::path third_socket_;
  std::filesystem::path occupied_;
};

class FileDescriptor {
 public:
  explicit FileDescriptor(int value) noexcept : value_(value) {}
  ~FileDescriptor() {
    if (value_ >= 0) (void)::close(value_);
  }
  FileDescriptor(FileDescriptor&& other) noexcept
      : value_(std::exchange(other.value_, -1)) {}

  FileDescriptor(const FileDescriptor&) = delete;
  FileDescriptor& operator=(const FileDescriptor&) = delete;
  FileDescriptor& operator=(FileDescriptor&&) = delete;

  int get() const noexcept { return value_; }

 private:
  int value_;
};

template <typename Expected, typename Result>
Expected take(Result result, std::string_view message) {
  pv::require(std::holds_alternative<Expected>(result), message);
  return std::get<Expected>(std::move(result));
}

pa::ApplicationV1 make_application(
    const std::filesystem::path& path,
    const p::Bytes& genesis) {
  auto ledger = ps::create_sqlite_ledger(path, genesis);
  pv::require(
      std::holds_alternative<ps::SQLiteLedger>(ledger.result),
      "create server test ledger");
  auto application = pa::make_application_v1(
      std::get<ps::SQLiteLedger>(std::move(ledger.result)));
  pv::require(
      std::holds_alternative<pa::ApplicationV1>(
          application.result),
      "create server test application");
  return std::get<pa::ApplicationV1>(
      std::move(application.result));
}

pa::UnixSocketServerV1 make_server(
    const std::filesystem::path& path) {
  auto server = pa::make_unix_socket_server_v1(path);
  pv::require(
      std::holds_alternative<pa::UnixSocketServerV1>(
          server.result),
      "create Unix server");
  return std::get<pa::UnixSocketServerV1>(
      std::move(server.result));
}

FileDescriptor connect_to(const std::filesystem::path& path) {
  FileDescriptor client(::socket(AF_UNIX, SOCK_STREAM, 0));
  pv::require(client.get() >= 0, "create Unix client");
  sockaddr_un address{};
  address.sun_family = AF_UNIX;
  pv::require(
      path.native().size() < sizeof(address.sun_path),
      "test socket path length");
  std::memcpy(
      address.sun_path, path.c_str(), path.native().size() + 1);
  pv::require(
      ::connect(
          client.get(),
          reinterpret_cast<const sockaddr*>(&address),
          sizeof(address)) == 0,
      "connect Unix client");
  return client;
}

void write_all(int socket, std::span<const std::uint8_t> bytes) {
  std::size_t offset = 0;
  while (offset < bytes.size()) {
    const auto count = ::send(
        socket, bytes.data() + offset, bytes.size() - offset,
        MSG_NOSIGNAL);
    if (count > 0) {
      offset += static_cast<std::size_t>(count);
      continue;
    }
    if (count < 0 && errno == EINTR) continue;
    throw std::runtime_error("write Unix test frame");
  }
}

void read_all(int socket, std::span<std::uint8_t> bytes) {
  std::size_t offset = 0;
  while (offset < bytes.size()) {
    const auto count = ::recv(
        socket, bytes.data() + offset, bytes.size() - offset, 0);
    if (count > 0) {
      offset += static_cast<std::size_t>(count);
      continue;
    }
    if (count < 0 && errno == EINTR) continue;
    throw std::runtime_error("read Unix test frame");
  }
}

p::Bytes info_request(std::uint64_t request_id) {
  auto encoded = pa::encode_frame(pa::Frame{
      pa::FrameHeader{
          pa::WireDirection::request,
          pa::MessageKind::info,
          request_id,
          0,
      },
      {},
  });
  return take<p::Bytes>(std::move(encoded), "encode Info request");
}

p::Bytes read_frame(int socket) {
  p::Bytes header(pa::kWireHeaderSize);
  read_all(socket, header);
  const auto decoded = take<pa::FrameHeader>(
      pa::decode_frame_header(header), "read response header");
  p::Bytes frame = header;
  frame.resize(pa::kWireHeaderSize + decoded.payload_size);
  read_all(
      socket,
      std::span<std::uint8_t>(frame).subspan(pa::kWireHeaderSize));
  return frame;
}

void verify_private_socket(const std::filesystem::path& path) {
  struct stat metadata {};
  pv::require(
      ::lstat(path.c_str(), &metadata) == 0 &&
          S_ISSOCK(metadata.st_mode) &&
          (metadata.st_mode & 0777) == 0600,
      "Unix socket is not owner-only");
}

void verify_reused_id_closes(
    pa::ApplicationV1& application,
    const std::filesystem::path& socket_path) {
  auto server = make_server(socket_path);
  verify_private_socket(socket_path);
  pa::ServeConnectionResult served;
  std::thread worker([&] {
    served = server.serve_connection(application);
  });

  auto client = connect_to(socket_path);
  const auto request = info_request(11);
  write_all(client.get(), request);
  const auto response = take<pa::Frame>(
      pa::decode_frame(read_frame(client.get())),
      "decode server response");
  pv::require(
      response.header ==
              pa::FrameHeader{
                  pa::WireDirection::response,
                  pa::MessageKind::info,
                  11,
                  54} &&
          response.payload.at(0) == 0 &&
          response.payload.at(1) == 0,
      "server Info response");

  write_all(client.get(), request);
  worker.join();
  pv::require(
      std::holds_alternative<pa::UnixServerError>(served) &&
          std::get<pa::UnixServerError>(served) ==
              pa::UnixServerError::protocol_failure,
      "reused request ID did not close connection");
  std::uint8_t byte = 0;
  pv::require(
      ::recv(client.get(), &byte, 1, 0) == 0,
      "protocol-failed connection remained open");
}

void verify_clean_disconnect(
    pa::ApplicationV1& application,
    const std::filesystem::path& socket_path) {
  auto server = make_server(socket_path);
  pa::ServeConnectionResult served;
  std::thread worker([&] {
    served = server.serve_connection(application);
  });
  {
    auto client = connect_to(socket_path);
    const auto request = info_request(12);
    write_all(client.get(), request);
    (void)read_frame(client.get());
  }
  worker.join();
  pv::require(
      std::holds_alternative<std::monostate>(served),
      "clean boundary EOF rejected");
}

void verify_truncated_disconnect(
    pa::ApplicationV1& application,
    const std::filesystem::path& socket_path) {
  auto server = make_server(socket_path);
  pa::ServeConnectionResult served;
  std::thread worker([&] {
    served = server.serve_connection(application);
  });
  {
    auto client = connect_to(socket_path);
    const auto request = info_request(13);
    write_all(
        client.get(),
        std::span<const std::uint8_t>(request).first(10));
    pv::require(
        ::shutdown(client.get(), SHUT_WR) == 0,
        "shutdown truncated client");
  }
  worker.join();
  pv::require(
      std::holds_alternative<pa::UnixServerError>(served) &&
          std::get<pa::UnixServerError>(served) ==
              pa::UnixServerError::protocol_failure,
      "truncated frame did not close connection");
}

void verify_path_failures(const std::filesystem::path& occupied) {
  {
    std::ofstream sentinel(occupied);
    sentinel << "owned";
  }
  auto result = pa::make_unix_socket_server_v1(occupied);
  pv::require(
      std::holds_alternative<pa::UnixServerError>(result.result) &&
          std::get<pa::UnixServerError>(result.result) ==
              pa::UnixServerError::path_in_use,
      "occupied socket path accepted");
  std::ifstream sentinel(occupied);
  std::string contents;
  sentinel >> contents;
  pv::require(contents == "owned", "occupied path was modified");

  auto relative =
      pa::make_unix_socket_server_v1("relative.sock");
  pv::require(
      std::holds_alternative<pa::UnixServerError>(
          relative.result) &&
          std::get<pa::UnixServerError>(relative.result) ==
              pa::UnixServerError::invalid_path,
      "relative socket path accepted");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc != 3) {
      throw std::runtime_error(
          "usage: unix_server_v1_test <ledger-vectors> <prefix>");
    }
    pv::require(sodium_init() >= 0, "libsodium initialization");
    TestFiles files(argv[2]);
    const auto values = pv::load_values(argv[1]);
    auto application = make_application(
        files.database(), pv::hex_decode(values.at("genesis")));
    verify_reused_id_closes(application, files.socket());
    pv::require(
        !std::filesystem::exists(files.socket()),
        "server destructor retained socket");
    verify_clean_disconnect(application, files.second_socket());
    pv::require(
        !std::filesystem::exists(files.second_socket()),
        "second server destructor retained socket");
    verify_truncated_disconnect(application, files.third_socket());
    pv::require(
        !std::filesystem::exists(files.third_socket()),
        "third server destructor retained socket");
    verify_path_failures(files.occupied());
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Unix server v1 tests: failed: "
              << error.what() << '\n';
    return 1;
  }
}

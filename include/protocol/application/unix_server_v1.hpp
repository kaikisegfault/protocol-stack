#pragma once

#include "protocol/application/application_v1.hpp"

#include <filesystem>
#include <memory>
#include <variant>

namespace protocol::application {

enum class UnixServerError : std::uint8_t {
  invalid_path = 1,
  path_in_use = 2,
  socket_failure = 3,
  accept_failure = 4,
  connection_failure = 5,
  protocol_failure = 6,
  application_failure = 7,
  shutdown_requested = 8,
};

using ServeConnectionResult =
    std::variant<std::monostate, UnixServerError>;

struct UnixSocketServerV1Result;

class UnixSocketServerV1 {
 public:
  ~UnixSocketServerV1() noexcept;
  UnixSocketServerV1(UnixSocketServerV1&&) noexcept;

  UnixSocketServerV1(const UnixSocketServerV1&) = delete;
  UnixSocketServerV1& operator=(const UnixSocketServerV1&) = delete;
  UnixSocketServerV1& operator=(UnixSocketServerV1&&) = delete;

  ServeConnectionResult serve_connection(
      ApplicationV1& application,
      int shutdown_descriptor = -1);

 private:
  struct Impl;

  explicit UnixSocketServerV1(
      std::unique_ptr<Impl> implementation) noexcept;

  friend UnixSocketServerV1Result make_unix_socket_server_v1(
      const std::filesystem::path& path);

  std::unique_ptr<Impl> implementation_;
};

struct UnixSocketServerV1Result {
  std::variant<UnixSocketServerV1, UnixServerError> result;
};

UnixSocketServerV1Result make_unix_socket_server_v1(
    const std::filesystem::path& path);

}  // namespace protocol::application

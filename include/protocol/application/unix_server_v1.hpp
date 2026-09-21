#pragma once

// A Unix socket that speaks the local application **wire**.
//
// The `V1` in this name is the socket's version, not the ledger's: the path
// rules, the bind, the ownership check, and the connection loop. The loop is one
// function over a wire version and a dispatcher, so each ledger version adds an
// overload here rather than a server.
//
// **Which wire an overload reads is part of its signature.** Versions one and
// eight read version-one frames, because the header, the seven message kinds,
// and the five request payloads carried no ledger-version meaning for them.
// Version nine reads version-two frames, because its blocks carry a timestamp —
// and a version-one frame offered to it is refused at the header, on the first
// frame, which is the refusal the version-two frame exists to make possible.

#include "protocol/application/application_v1.hpp"
#include "protocol/application/application_v8.hpp"
#include "protocol/application/application_v9.hpp"

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
  ServeConnectionResult serve_connection(
      ApplicationV8& application,
      int shutdown_descriptor = -1);
  // Version-two frames.
  ServeConnectionResult serve_connection(
      ApplicationV9& application,
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

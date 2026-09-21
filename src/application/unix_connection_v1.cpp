#include "protocol/application/unix_server_v1.hpp"

#include "unix_server_v1_internal.hpp"

#include "protocol/application/dispatcher_v1.hpp"
#include "protocol/application/dispatcher_v8.hpp"
#include "protocol/application/dispatcher_v9.hpp"
#include "protocol/application/wire_v1.hpp"
#include "protocol/application/wire_v2.hpp"

#include <poll.h>
#include <span>
#include <sys/socket.h>
#include <unordered_set>
#include <utility>
#include <variant>

namespace protocol::application {
namespace {

using internal::FileDescriptor;
using protocol::v1::Bytes;

enum class ReadResult {
  complete,
  clean_eof,
  interrupted,
  failure,
};

enum class WriteResult {
  complete,
  interrupted,
  failure,
};

enum class WaitResult {
  ready,
  interrupted,
  failure,
};

WaitResult wait_for(
    int socket,
    short events,
    int shutdown_descriptor) noexcept {
  pollfd descriptors[2]{
      pollfd{socket, events, 0},
      pollfd{shutdown_descriptor, POLLIN, 0},
  };
  const auto count = shutdown_descriptor >= 0 ? 2U : 1U;
  const auto polled = ::poll(descriptors, count, -1);
  if (polled < 0 || (descriptors[0].revents & POLLNVAL) != 0) {
    return WaitResult::failure;
  }
  if (count == 2U && descriptors[1].revents != 0) {
    return WaitResult::interrupted;
  }
  return (descriptors[0].revents &
          (events | POLLERR | POLLHUP)) != 0
             ? WaitResult::ready
             : WaitResult::failure;
}

ReadResult read_exact(
    int socket,
    std::span<std::uint8_t> output,
    bool boundary_eof_is_clean,
    int shutdown_descriptor) noexcept {
  std::size_t offset = 0;
  while (offset < output.size()) {
    const auto ready =
        wait_for(socket, POLLIN, shutdown_descriptor);
    if (ready == WaitResult::interrupted) {
      return ReadResult::interrupted;
    }
    if (ready != WaitResult::ready) return ReadResult::failure;
    const auto count = ::recv(
        socket, output.data() + offset, output.size() - offset, 0);
    if (count > 0) {
      offset += static_cast<std::size_t>(count);
      continue;
    }
    if (count == 0) {
      return boundary_eof_is_clean && offset == 0
                 ? ReadResult::clean_eof
                 : ReadResult::failure;
    }
    return ReadResult::failure;
  }
  return ReadResult::complete;
}

WriteResult write_exact(
    int socket,
    std::span<const std::uint8_t> input,
    int shutdown_descriptor) noexcept {
  std::size_t offset = 0;
  while (offset < input.size()) {
    const auto ready =
        wait_for(socket, POLLOUT, shutdown_descriptor);
    if (ready == WaitResult::interrupted) {
      return WriteResult::interrupted;
    }
    if (ready != WaitResult::ready) return WriteResult::failure;
    const auto count = ::send(
        socket, input.data() + offset, input.size() - offset,
        MSG_NOSIGNAL);
    if (count > 0) {
      offset += static_cast<std::size_t>(count);
      continue;
    }
    return WriteResult::failure;
  }
  return WriteResult::complete;
}

// The two wire versions, as the loop needs them: a header decoder, a request
// decoder, and the request type the second produces. They differ in the accepted
// version octet and in two payloads, and in nothing the loop reads.
struct WireV1 {
  using Request = DecodedRequest;
  static HeaderResult header(std::span<const std::uint8_t> bytes) noexcept {
    return decode_frame_header(bytes);
  }
  static RequestResult request(std::span<const std::uint8_t> bytes) {
    return decode_request_frame(bytes);
  }
};

struct WireV2 {
  using Request = DecodedRequestV2;
  static HeaderResult header(std::span<const std::uint8_t> bytes) noexcept {
    return decode_frame_header_v2(bytes);
  }
  static RequestResultV2 request(std::span<const std::uint8_t> bytes) {
    return decode_request_frame_v2(bytes);
  }
};

// The connection loop is one function over a wire and a dispatcher, because
// everything in it — accepting, framing, the duplicate-request-id rule, the
// shutdown descriptor — is a property of the socket rather than of a ledger or
// frame version. Two copies of it would be two places for a framing rule to be
// wrong.
template <typename Wire, typename Dispatch>
ServeConnectionResult serve_with(
    int listener,
    int shutdown_descriptor,
    Dispatch dispatch) {
  const auto listener_ready = wait_for(
      listener, POLLIN, shutdown_descriptor);
  if (listener_ready == WaitResult::interrupted) {
    return UnixServerError::shutdown_requested;
  }
  if (listener_ready != WaitResult::ready) {
    return UnixServerError::accept_failure;
  }
  FileDescriptor client(::accept(listener, nullptr, nullptr));
  if (client.get() < 0) return UnixServerError::accept_failure;

  std::unordered_set<std::uint64_t> request_ids;
  for (;;) {
    Bytes header(kWireHeaderSize);
    const auto header_read = read_exact(
        client.get(), header, true, shutdown_descriptor);
    if (header_read == ReadResult::interrupted) {
      return UnixServerError::shutdown_requested;
    }
    if (header_read == ReadResult::clean_eof) return std::monostate{};
    if (header_read != ReadResult::complete) {
      return UnixServerError::protocol_failure;
    }
    auto decoded_header = Wire::header(header);
    if (!std::holds_alternative<FrameHeader>(decoded_header)) {
      return UnixServerError::protocol_failure;
    }
    const auto fields = std::get<FrameHeader>(decoded_header);
    if (fields.direction != WireDirection::request ||
        !request_ids.insert(fields.request_id).second) {
      return UnixServerError::protocol_failure;
    }

    Bytes frame;
    frame.reserve(kWireHeaderSize + fields.payload_size);
    frame.insert(frame.end(), header.begin(), header.end());
    frame.resize(kWireHeaderSize + fields.payload_size);
    const auto payload = std::span<std::uint8_t>(frame).subspan(
        kWireHeaderSize);
    const auto payload_read = read_exact(
        client.get(), payload, false, shutdown_descriptor);
    if (payload_read == ReadResult::interrupted) {
      return UnixServerError::shutdown_requested;
    }
    if (payload_read != ReadResult::complete) {
      return UnixServerError::protocol_failure;
    }
    auto request = Wire::request(frame);
    using Request = typename Wire::Request;
    if (!std::holds_alternative<Request>(request)) {
      return UnixServerError::protocol_failure;
    }
    auto response = dispatch(std::get<Request>(std::move(request)));
    if (!std::holds_alternative<Bytes>(response)) {
      return UnixServerError::application_failure;
    }
    const auto written = write_exact(
        client.get(), std::get<Bytes>(response),
        shutdown_descriptor);
    if (written == WriteResult::interrupted) {
      return UnixServerError::shutdown_requested;
    }
    if (written != WriteResult::complete) {
      return UnixServerError::connection_failure;
    }
  }
}

}  // namespace

ServeConnectionResult UnixSocketServerV1::serve_connection(
    ApplicationV1& application,
    int shutdown_descriptor) {
  return serve_with<WireV1>(
      implementation_->listener, shutdown_descriptor,
      [&application](const DecodedRequest& request) {
        return dispatch_request(application, request);
      });
}

ServeConnectionResult UnixSocketServerV1::serve_connection(
    ApplicationV8& application,
    int shutdown_descriptor) {
  return serve_with<WireV1>(
      implementation_->listener, shutdown_descriptor,
      [&application](const DecodedRequest& request) {
        return dispatch_request_v8(application, request);
      });
}

ServeConnectionResult UnixSocketServerV1::serve_connection(
    ApplicationV9& application,
    int shutdown_descriptor) {
  return serve_with<WireV2>(
      implementation_->listener, shutdown_descriptor,
      [&application](const DecodedRequestV2& request) {
        return dispatch_request_v9(application, request);
      });
}

}  // namespace protocol::application

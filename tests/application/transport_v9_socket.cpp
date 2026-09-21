// The version-nine frames over a real socket, which is the only thing that
// exercises `serve_connection(ApplicationV9&)` — and therefore the only thing
// that proves the shared connection loop reads a version-two header when it is
// serving version nine.
//
// **The second connection is the one that states the point of the version.** A
// version-one frame offered to the version-nine overload must be refused at the
// header, before a payload decoder or the application is reached, and the
// connection must end without a response being written. Before version two that
// refusal landed at the result count on the first finalized block.

#include "protocol/application/unix_server_v1.hpp"

#include "transport_v9_support.hpp"

#include <cerrno>
#include <cstring>
#include <exception>
#include <sys/socket.h>
#include <sys/un.h>
#include <thread>
#include <unistd.h>

namespace transport_v9_tests {
namespace {

class ClientSocket {
 public:
  explicit ClientSocket(const std::filesystem::path& path) {
    descriptor_ = ::socket(AF_UNIX, SOCK_STREAM, 0);
    pv::require(descriptor_ >= 0, "the client socket opens");
    sockaddr_un address{};
    address.sun_family = AF_UNIX;
    pv::require(path.native().size() < sizeof(address.sun_path),
                "the socket pathname fits in sun_path");
    std::memcpy(address.sun_path, path.c_str(), path.native().size() + 1);
    pv::require(::connect(descriptor_, reinterpret_cast<const sockaddr*>(&address),
                          sizeof(address)) == 0,
                "the client connects");
  }
  ~ClientSocket() {
    if (descriptor_ >= 0) (void)::close(descriptor_);
  }
  ClientSocket(const ClientSocket&) = delete;
  ClientSocket& operator=(const ClientSocket&) = delete;

  void close_now() {
    if (descriptor_ >= 0) (void)::close(descriptor_);
    descriptor_ = -1;
  }

  void write_all(std::span<const std::uint8_t> bytes) const {
    std::size_t offset = 0;
    while (offset < bytes.size()) {
      const auto count = ::send(descriptor_, bytes.data() + offset,
                                bytes.size() - offset, MSG_NOSIGNAL);
      if (count > 0) {
        offset += static_cast<std::size_t>(count);
        continue;
      }
      if (count < 0 && errno == EINTR) continue;
      pv::require(false, "the client wrote its frame");
    }
  }

  void read_all(std::span<std::uint8_t> bytes) const {
    std::size_t offset = 0;
    while (offset < bytes.size()) {
      const auto count =
          ::recv(descriptor_, bytes.data() + offset, bytes.size() - offset, 0);
      if (count > 0) {
        offset += static_cast<std::size_t>(count);
        continue;
      }
      if (count < 0 && errno == EINTR) continue;
      pv::require(false, "the client read its frame");
    }
  }

  // The server's side of the connection closed with nothing written.
  bool closed_without_reply() const {
    std::uint8_t octet = 0;
    for (;;) {
      const auto count = ::recv(descriptor_, &octet, 1, 0);
      if (count < 0 && errno == EINTR) continue;
      return count == 0;
    }
  }

  // The response header is read with version two's decoder, so an answer on the
  // wrong frame version fails here rather than being read as a body.
  Bytes exchange_frame(const Bytes& request) const {
    write_all(request);
    Bytes frame(kHeaderSize);
    read_all(frame);
    auto decoded = pa::decode_frame_header_v2(frame);
    pv::require(std::holds_alternative<pa::FrameHeader>(decoded),
                "the response header decodes as version two's");
    frame.resize(kHeaderSize + std::get<pa::FrameHeader>(decoded).payload_size);
    read_all(std::span<std::uint8_t>(frame).subspan(kHeaderSize));
    return frame;
  }

 private:
  int descriptor_ = -1;
};

// Serve one connection on a worker while `client` runs, and report a client
// failure rather than abort: an unjoined `std::thread` calls `std::terminate`,
// and the server returns only once the client's socket is closed — which the
// destructor does as the exception leaves the block.
template <typename Client>
pa::ServeConnectionResult serve_one(pa::UnixSocketServerV1& server,
                                    pa::ApplicationV9& application, Client client) {
  pa::ServeConnectionResult served;
  std::thread worker([&] { served = server.serve_connection(application); });
  std::exception_ptr failure;
  try {
    client();
  } catch (...) {
    failure = std::current_exception();
  }
  worker.join();
  if (failure) std::rethrow_exception(failure);
  return served;
}

Response over(const ClientSocket& client, pa::MessageKind kind, std::uint64_t id,
              const Bytes& payload, const std::string& subject) {
  auto response = read_response(client.exchange_frame(request_frame(kind, id, payload)),
                                kind, id, subject);
  pv::require(response.status == 0, subject + ": answered status " +
                                        std::to_string(response.status));
  return response;
}

}  // namespace

void check_over_a_socket(const pv::Values& values,
                         const std::filesystem::path& directory) {
  CountingClock clock;
  auto application = open_application(directory / "socket.db", true, clock);
  const auto socket_path = directory / "s";
  auto made = pa::make_unix_socket_server_v1(socket_path);
  pv::require(std::holds_alternative<pa::UnixSocketServerV1>(made.result),
              "the Unix socket server binds");
  auto server = std::get<pa::UnixSocketServerV1>(std::move(made.result));

  const auto label = block_label(0);
  const auto height = recorded_number(values, label + ".height");
  const auto stamp = recorded_number(values, label + ".timestamp");
  const auto root = recorded(values, label + ".resulting_state_root");
  const auto payload = block_payload(height, stamp, restart_run().block_inputs[0]);
  *clock.now = stamp;

  auto served = serve_one(server, application, [&] {
    ClientSocket client(socket_path);
    (void)over(client, pa::MessageKind::init_chain, 1,
               init_chain_payload(fixture::kGenesisMillis), "init_chain over the socket");
    pv::require(over(client, pa::MessageKind::process_proposal, 2, payload,
                     "process_proposal over the socket").body == Bytes{0},
                "the socket's proposal was not decision 0");
    Reader finalized(over(client, pa::MessageKind::finalize_block, 3, payload,
                          "finalize_block over the socket").body);
    pv::require(fixture::hex(finalized.hash()) == root,
                "the socket's root is not the recorded one");
    pv::require(fixture::hex(finalized.hash()) == recorded(values, label + ".block_id"),
                "the socket's block identifier is not the recorded one");
    Reader committed(
        over(client, pa::MessageKind::commit, 4, {}, "commit over the socket").body);
    pv::require(committed.u64() == height && committed.u64() == stamp &&
                    fixture::hex(committed.hash()) == root,
                "the socket's commit is not the recorded head");
    committed.require_finished("commit over the socket");
    client.close_now();
  });
  // A client that closes cleanly ends the connection without an error, which is
  // what an adapter restarting looks like from this side.
  pv::require(std::holds_alternative<std::monostate>(served),
              "a clean disconnect must not be an error");
  pv::require(clock.reads->load() == 1, "the socket read the clock more than once");

  auto refused = serve_one(server, application, [&] {
    ClientSocket client(socket_path);
    client.write_all(request_frame(pa::MessageKind::info, 1, {}, 1));
    pv::require(client.closed_without_reply(),
                "a version-one frame was answered by the version-nine socket");
  });
  pv::require(std::holds_alternative<pa::UnixServerError>(refused) &&
                  std::get<pa::UnixServerError>(refused) ==
                      pa::UnixServerError::protocol_failure,
              "a version-one frame did not end the connection as a protocol failure");
}

}  // namespace transport_v9_tests

#include "protocol/application/unix_server_v1.hpp"

#include "unix_server_v1_internal.hpp"

#include <cerrno>
#include <cstring>
#include <memory>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>
#include <utility>

namespace protocol::application {
namespace {

using internal::FileDescriptor;

bool path_fits_socket(const std::filesystem::path& path) {
  const auto native = path.native();
  return path.is_absolute() && !native.empty() &&
         native.size() < sizeof(sockaddr_un{}.sun_path);
}

UnixServerError socket_error(int error) noexcept {
  return error == EADDRINUSE ? UnixServerError::path_in_use
                             : UnixServerError::socket_failure;
}

enum class ExistingSocket {
  removed,
  in_use,
  failure,
};

ExistingSocket remove_stale_socket(
    const std::filesystem::path& path,
    const sockaddr_un& address) noexcept {
  struct stat before {};
  if (::lstat(path.c_str(), &before) != 0 ||
      !S_ISSOCK(before.st_mode) ||
      before.st_uid != ::geteuid()) {
    return ExistingSocket::in_use;
  }

  FileDescriptor probe(::socket(AF_UNIX, SOCK_STREAM, 0));
  if (probe.get() < 0) return ExistingSocket::failure;
  if (::connect(
          probe.get(),
          reinterpret_cast<const sockaddr*>(&address),
          sizeof(address)) == 0) {
    return ExistingSocket::in_use;
  }
  if (errno != ECONNREFUSED) return ExistingSocket::in_use;

  struct stat after {};
  if (::lstat(path.c_str(), &after) != 0 ||
      before.st_dev != after.st_dev ||
      before.st_ino != after.st_ino ||
      before.st_mode != after.st_mode ||
      before.st_uid != after.st_uid) {
    return ExistingSocket::failure;
  }
  return ::unlink(path.c_str()) == 0
             ? ExistingSocket::removed
             : ExistingSocket::failure;
}

}  // namespace

UnixSocketServerV1::Impl::Impl(
    int owned_listener,
    std::filesystem::path owned_path,
    dev_t created_device,
    ino_t created_inode)
    : listener(owned_listener),
      path(std::move(owned_path)),
      device(created_device),
      inode(created_inode) {}

UnixSocketServerV1::Impl::~Impl() noexcept {
  if (listener >= 0) (void)::close(listener);
  struct stat current {};
  if (::lstat(path.c_str(), &current) == 0 &&
      current.st_dev == device && current.st_ino == inode) {
    (void)::unlink(path.c_str());
  }
}

UnixSocketServerV1::UnixSocketServerV1(
    std::unique_ptr<Impl> implementation) noexcept
    : implementation_(std::move(implementation)) {}

UnixSocketServerV1::~UnixSocketServerV1() noexcept = default;
UnixSocketServerV1::UnixSocketServerV1(
    UnixSocketServerV1&&) noexcept = default;

UnixSocketServerV1Result make_unix_socket_server_v1(
    const std::filesystem::path& path) {
  if (!path_fits_socket(path)) {
    return UnixSocketServerV1Result{
        std::variant<UnixSocketServerV1, UnixServerError>(
            std::in_place_type<UnixServerError>,
            UnixServerError::invalid_path),
    };
  }

  FileDescriptor listener(::socket(AF_UNIX, SOCK_STREAM, 0));
  if (listener.get() < 0) {
    return UnixSocketServerV1Result{
        std::variant<UnixSocketServerV1, UnixServerError>(
            std::in_place_type<UnixServerError>,
            UnixServerError::socket_failure),
    };
  }
  sockaddr_un address{};
  address.sun_family = AF_UNIX;
  std::memcpy(
      address.sun_path, path.c_str(), path.native().size() + 1);
  if (::bind(
          listener.get(),
          reinterpret_cast<const sockaddr*>(&address),
          sizeof(address)) != 0) {
    const auto bind_error = errno;
    if (bind_error != EADDRINUSE ||
        remove_stale_socket(path, address) !=
            ExistingSocket::removed ||
        ::bind(
            listener.get(),
            reinterpret_cast<const sockaddr*>(&address),
            sizeof(address)) != 0) {
      const auto error =
          bind_error == EADDRINUSE
              ? UnixServerError::path_in_use
              : socket_error(bind_error);
      return UnixSocketServerV1Result{
          std::variant<UnixSocketServerV1, UnixServerError>(
              std::in_place_type<UnixServerError>, error),
      };
    }
  }
  if (::chmod(path.c_str(), S_IRUSR | S_IWUSR) != 0 ||
      ::listen(listener.get(), 1) != 0) {
    (void)::unlink(path.c_str());
    return UnixSocketServerV1Result{
        std::variant<UnixSocketServerV1, UnixServerError>(
            std::in_place_type<UnixServerError>,
            UnixServerError::socket_failure),
    };
  }
  struct stat created {};
  if (::lstat(path.c_str(), &created) != 0 ||
      !S_ISSOCK(created.st_mode)) {
    (void)::unlink(path.c_str());
    return UnixSocketServerV1Result{
        std::variant<UnixSocketServerV1, UnixServerError>(
            std::in_place_type<UnixServerError>,
            UnixServerError::socket_failure),
    };
  }

  return UnixSocketServerV1Result{
      std::variant<UnixSocketServerV1, UnixServerError>(
          std::in_place_type<UnixSocketServerV1>,
          UnixSocketServerV1(std::make_unique<UnixSocketServerV1::Impl>(
              listener.release(), path, created.st_dev,
              created.st_ino))),
  };
}

}  // namespace protocol::application

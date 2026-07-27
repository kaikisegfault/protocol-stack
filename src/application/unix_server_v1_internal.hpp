#pragma once

#include "protocol/application/unix_server_v1.hpp"

#include <filesystem>
#include <sys/types.h>
#include <unistd.h>
#include <utility>

namespace protocol::application::internal {

class FileDescriptor {
 public:
  explicit FileDescriptor(int value = -1) noexcept : value_(value) {}
  ~FileDescriptor() noexcept {
    if (value_ >= 0) (void)::close(value_);
  }
  FileDescriptor(FileDescriptor&& other) noexcept
      : value_(std::exchange(other.value_, -1)) {}

  FileDescriptor(const FileDescriptor&) = delete;
  FileDescriptor& operator=(const FileDescriptor&) = delete;
  FileDescriptor& operator=(FileDescriptor&&) = delete;

  int get() const noexcept { return value_; }
  int release() noexcept { return std::exchange(value_, -1); }

 private:
  int value_;
};

}  // namespace protocol::application::internal

namespace protocol::application {

struct UnixSocketServerV1::Impl {
  int listener;
  std::filesystem::path path;
  dev_t device;
  ino_t inode;

  Impl(
      int owned_listener,
      std::filesystem::path owned_path,
      dev_t created_device,
      ino_t created_inode);
  ~Impl() noexcept;
};

}  // namespace protocol::application

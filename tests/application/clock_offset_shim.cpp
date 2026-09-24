// `libprotocol-clock-offset.so`: a test-only library, loaded with `LD_PRELOAD`,
// that moves one process's real-time clock and nothing else.
//
// **Why it exists.** `consensus-application-v2` wants one devnet replica's clock
// beyond the tolerance, and it also says that in a deployment the application's
// clock source *is* the platform real-time clock. ADR 0085 adds that the process
// takes no flag that offsets or replaces it. A skew applied here leaves both
// true: the binary under test is the one that ships, and the clock is wrong where
// a real machine's clock is wrong, below the process. ADR 0091 records the
// choice against an operator option.
//
// **What it moves.** `clock_gettime(CLOCK_REALTIME, ...)`, which is the one
// read `protocol-application-v9` makes (ADR 0085). Every other clock passes
// through untouched, so poll and socket timeouts keep running on real time.
//
// **Where the offset comes from.** A file named by
// `PROTOCOL_STACK_CLOCK_OFFSET_FILE`, holding a signed decimal count of
// milliseconds — an optional sign, one to twelve digits, and an optional newline.
// It is read on **every** call, so a test can move the clock of a process that
// is already running. That is what lets one run show a replica ahead, then
// behind, then corrected. The application reads its clock once per
// `ProcessProposal`, so the cost is a few system calls per proposal.
//
// **An unreadable offset is an unreadable clock.** A missing variable, a missing
// file, or a malformed figure makes the call fail with `EINVAL`. It does not
// quietly return the real time, because a shim that fell back would let a
// misconfigured run pass as a skewed one. It also gives the headless test the
// two paths ADR 0085 could not reach without faking the clock: a process that
// cannot read its clock at startup, and one whose clock stops being readable.
//
// **Only raw system calls.** The real clock, the file, and the descriptor are
// all reached through `syscall(2)`, never through a libc function that a
// sanitizer runtime intercepts, and nothing is allocated. So the shim has no
// ordering relationship with ASan to get wrong, which is why the one ASan
// option the harness sets (`verify_asan_link_order=0`) is safe.

#include <cerrno>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <ctime>
#include <fcntl.h>
#include <sys/syscall.h>
#include <unistd.h>

namespace {

constexpr const char* kOffsetFileVariable = "PROTOCOL_STACK_CLOCK_OFFSET_FILE";
// Twelve digits is about thirty-one years of milliseconds: far beyond any skew
// a test needs, and far below anything that could overflow a `time_t`.
constexpr std::size_t kMaximumDigits = 12;
// A sign, the digits, and a newline. One octet more is read so that a longer
// file is seen to be longer rather than silently truncated.
constexpr std::size_t kMaximumFileBytes = 1 + kMaximumDigits + 1;
constexpr std::int64_t kNanosPerSecond = 1'000'000'000;
constexpr std::int64_t kNanosPerMilli = 1'000'000;

bool parse_offset(const char* text, std::size_t size,
                  std::int64_t& offset) noexcept {
  std::size_t index = 0;
  bool negative = false;
  if (index < size && (text[index] == '+' || text[index] == '-')) {
    negative = text[index] == '-';
    ++index;
  }
  const std::size_t first_digit = index;
  std::int64_t magnitude = 0;
  while (index < size && text[index] >= '0' && text[index] <= '9') {
    if (index - first_digit == kMaximumDigits) return false;
    magnitude = magnitude * 10 + (text[index] - '0');
    ++index;
  }
  if (index == first_digit) return false;
  if (index < size && text[index] == '\n') ++index;
  if (index != size) return false;
  offset = negative ? -magnitude : magnitude;
  return true;
}

bool read_offset(std::int64_t& offset) noexcept {
  const char* path = std::getenv(kOffsetFileVariable);
  if (path == nullptr || path[0] != '/') return false;
  const long descriptor =
      ::syscall(SYS_openat, AT_FDCWD, path, O_RDONLY | O_CLOEXEC);
  if (descriptor < 0) return false;
  char buffer[kMaximumFileBytes + 1];
  std::size_t size = 0;
  bool complete = false;
  while (size < sizeof buffer) {
    const long count =
        ::syscall(SYS_read, descriptor, buffer + size, sizeof buffer - size);
    if (count < 0 && errno == EINTR) continue;
    if (count < 0) break;
    if (count == 0) {
      complete = true;
      break;
    }
    size += static_cast<std::size_t>(count);
  }
  (void)::syscall(SYS_close, descriptor);
  return complete && parse_offset(buffer, size, offset);
}

}  // namespace

// The signature is glibc's own, `noexcept` included, so this definition
// interposes on the one every caller in the process resolves to.
extern "C" int clock_gettime(clockid_t clock, timespec* value) noexcept {
  if (::syscall(SYS_clock_gettime, clock, value) != 0) return -1;
  if (clock != CLOCK_REALTIME) return 0;
  const int saved = errno;
  std::int64_t offset = 0;
  if (!read_offset(offset)) {
    errno = EINVAL;
    return -1;
  }
  errno = saved;
  std::int64_t seconds = value->tv_sec + offset / 1000;
  std::int64_t nanos = value->tv_nsec + (offset % 1000) * kNanosPerMilli;
  if (nanos < 0) {
    nanos += kNanosPerSecond;
    --seconds;
  } else if (nanos >= kNanosPerSecond) {
    nanos -= kNanosPerSecond;
    ++seconds;
  }
  value->tv_sec = static_cast<time_t>(seconds);
  value->tv_nsec = static_cast<long>(nanos);
  return 0;
}

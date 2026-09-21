#pragma once

// What the version-nine transport suite's three translation units share: the
// octets an adapter would send, a reader over the octets it would get back, the
// clock that counts, and the one exchange every case is written in terms of.
//
// **Every response is taken apart from its own frame**, header first: the
// magic, the frame version — which must be `2` on every answer, error or not —
// the direction, the kind that was asked, the identifier that was chosen, a
// declared size that matches what arrived, and an empty diagnostic. A case that
// read only the body would pass against an encoder that answered on the wrong
// frame version, which is the one fault this whole version exists to name.

#include "protocol/application/application_v9.hpp"
#include "protocol/application/dispatcher_v9.hpp"
#include "protocol/application/wire_v2.hpp"

#include "../storage/sqlite_ledger_v9_fixture.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <span>
#include <string>
#include <utility>
#include <variant>
#include <vector>

namespace transport_v9_tests {

using namespace sqlite_ledger_v9_tests;
namespace pa = protocol::application;
using Bytes = v9::Bytes;

inline constexpr std::uint8_t kAppStateV9[] = {
    '"', 'p', 'r', 'o', 't', 'o', 'c', 'o', 'l', '-',
    's', 't', 'a', 'c', 'k', '-', 'v', '9', '"',
};
inline constexpr std::array<std::uint8_t, 4> kMagic{'P', 'S', 'A', 'P'};
inline constexpr std::size_t kHeaderSize = 20;
inline constexpr std::size_t kStatusSize = 6;

// Pinned to the literal: the header check below compares what the wire carried
// against it, which is a claim about the encoding and not about the constant.
static_assert(pa::kWireVersionV2 == 2);

inline void append_u16(Bytes& output, std::uint16_t value) {
  output.push_back(static_cast<std::uint8_t>(value >> 8U));
  output.push_back(static_cast<std::uint8_t>(value));
}

inline void append_u32(Bytes& output, std::uint32_t value) {
  for (int shift = 24; shift >= 0; shift -= 8) {
    output.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

inline void append_u64(Bytes& output, std::uint64_t value) {
  for (int shift = 56; shift >= 0; shift -= 8) {
    output.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

inline void append_blob(Bytes& output, std::span<const std::uint8_t> bytes) {
  append_u32(output, static_cast<std::uint32_t>(bytes.size()));
  output.insert(output.end(), bytes.begin(), bytes.end());
}

inline void append_transactions(Bytes& output, std::span<const Bytes> transactions) {
  append_u32(output, static_cast<std::uint32_t>(transactions.size()));
  for (const auto& transaction : transactions) append_blob(output, transaction);
}

// The exact octets an adapter would put on the socket, at a chosen frame
// version so a case can offer version one's to a version-two reader.
inline Bytes request_frame(pa::MessageKind kind, std::uint64_t request_id,
                           const Bytes& payload,
                           std::uint16_t version = pa::kWireVersionV2) {
  Bytes frame(kMagic.begin(), kMagic.end());
  append_u16(frame, version);
  frame.push_back(static_cast<std::uint8_t>(pa::WireDirection::request));
  frame.push_back(static_cast<std::uint8_t>(kind));
  append_u64(frame, request_id);
  append_u32(frame, static_cast<std::uint32_t>(payload.size()));
  frame.insert(frame.end(), payload.begin(), payload.end());
  return frame;
}

// A reader over a response payload, walking the octets the way an adapter must
// and refusing to finish with anything left over.
class Reader {
 public:
  explicit Reader(std::span<const std::uint8_t> bytes) : bytes_(bytes) {}

  std::uint64_t number(std::size_t width) {
    pv::require(bytes_.size() - offset_ >= width, "the payload is too short");
    std::uint64_t value = 0;
    for (std::size_t index = 0; index < width; ++index) {
      value = (value << 8U) | bytes_[offset_ + index];
    }
    offset_ += width;
    return value;
  }
  std::uint8_t u8() { return static_cast<std::uint8_t>(number(1)); }
  std::uint32_t u32() { return static_cast<std::uint32_t>(number(4)); }
  std::uint64_t u64() { return number(8); }

  v9::Octets32 hash() {
    pv::require(bytes_.size() - offset_ >= 32, "the payload has no hash left");
    v9::Octets32 value{};
    std::copy_n(bytes_.begin() + static_cast<std::ptrdiff_t>(offset_), 32,
                value.begin());
    offset_ += 32;
    return value;
  }

  Bytes blob() {
    const auto size = u32();
    pv::require(bytes_.size() - offset_ >= size, "the payload has no blob left");
    const auto begin = bytes_.begin() + static_cast<std::ptrdiff_t>(offset_);
    offset_ += size;
    return Bytes(begin, begin + static_cast<std::ptrdiff_t>(size));
  }

  void require_finished(const std::string& subject) const {
    pv::require(offset_ == bytes_.size(),
                subject + ": the response payload has trailing octets");
  }

 private:
  std::span<const std::uint8_t> bytes_;
  std::size_t offset_ = 0;
};

struct Response {
  std::uint16_t status = 0;
  Bytes body;
};

// Take one response frame apart and check the header an adapter would check.
inline Response read_response(const Bytes& frame, pa::MessageKind kind,
                              std::uint64_t request_id, const std::string& subject) {
  pv::require(frame.size() >= kHeaderSize + kStatusSize,
              subject + ": the response is shorter than a header and a status");
  Reader header(frame);
  pv::require(std::equal(kMagic.begin(), kMagic.end(), frame.begin()),
              subject + ": the response carries the wrong magic");
  (void)header.number(4);
  pv::require(header.number(2) == 2, subject + ": the response is not a version-two frame");
  pv::require(header.u8() == static_cast<std::uint8_t>(pa::WireDirection::response),
              subject + ": the response is not marked as one");
  pv::require(header.u8() == static_cast<std::uint8_t>(kind),
              subject + ": the response answers a different kind");
  pv::require(header.u64() == request_id,
              subject + ": the response answers a different request");
  pv::require(header.u32() == frame.size() - kHeaderSize,
              subject + ": the declared payload size is not the payload's");
  Response response;
  response.status = static_cast<std::uint16_t>(header.number(2));
  pv::require(header.u32() == 0, subject + ": the response carries a diagnostic");
  response.body.assign(frame.begin() + kHeaderSize + kStatusSize, frame.end());
  pv::require(response.status == 0 || response.body.empty(),
              subject + ": an error response carries a body");
  return response;
}

// Dispatch one request frame **once**, as `wire_v2` decodes it.
inline Response exchange(pa::ApplicationV9& application, pa::MessageKind kind,
                         std::uint64_t request_id, const Bytes& payload,
                         const std::string& subject) {
  auto decoded = pa::decode_request_frame_v2(request_frame(kind, request_id, payload));
  pv::require(std::holds_alternative<pa::DecodedRequestV2>(decoded),
              subject + ": the request frame did not decode");
  auto encoded = pa::dispatch_request_v9(
      application, std::get<pa::DecodedRequestV2>(std::move(decoded)));
  pv::require(std::holds_alternative<Bytes>(encoded),
              subject + ": the response did not encode");
  return read_response(std::get<Bytes>(encoded), kind, request_id, subject);
}

inline Response require_ok(pa::ApplicationV9& application, pa::MessageKind kind,
                           std::uint64_t request_id, const Bytes& payload,
                           const std::string& subject) {
  auto response = exchange(application, kind, request_id, payload, subject);
  pv::require(response.status == 0, subject + ": the application answered status " +
                                        std::to_string(response.status));
  return response;
}

inline void require_status(pa::ApplicationV9& application, pa::MessageKind kind,
                           std::uint64_t request_id, const Bytes& payload,
                           std::uint16_t expected, const std::string& subject) {
  const auto response = exchange(application, kind, request_id, payload, subject);
  pv::require(response.status == expected,
              subject + ": expected status " + std::to_string(expected) + ", got " +
                  std::to_string(response.status));
}

// A decision is one octet under status zero.
inline void require_decision(pa::ApplicationV9& application, std::uint64_t request_id,
                             const Bytes& payload, pa::ProposalDecision expected,
                             const std::string& subject) {
  Reader reader(require_ok(application, pa::MessageKind::process_proposal, request_id,
                           payload, subject).body);
  const auto actual = reader.u8();
  pv::require(actual == static_cast<std::uint8_t>(expected),
              subject + ": expected decision " +
                  std::to_string(static_cast<unsigned>(expected)) + ", got " +
                  std::to_string(static_cast<unsigned>(actual)));
  reader.require_finished(subject);
}

// **A clock that counts**, as `application_v9_test.cpp`'s does. Here it measures
// the dispatcher rather than the application: a dispatcher that asked for a vote
// before finalizing, or answered Info by way of a proposal, would read it.
struct CountingClock {
  std::shared_ptr<std::uint64_t> now = std::make_shared<std::uint64_t>(0);
  std::shared_ptr<std::atomic<std::size_t>> reads =
      std::make_shared<std::atomic<std::size_t>>(0);

  pa::ClockSourceV9 source() const {
    return [value = now, counter = reads]() -> std::uint64_t {
      counter->fetch_add(1);
      return *value;
    };
  }
};

inline pa::ApplicationV9 open_application(const std::filesystem::path& path,
                                          bool create, const CountingClock& clock) {
  const auto genesis = fixture::trace_genesis();
  auto store = require_store(
      create ? ps::create_sqlite_ledger_v9(path, genesis, trace_verifier())
             : ps::open_sqlite_ledger_v9(path, genesis, trace_verifier()),
      create ? "creating the store" : "reopening the store");
  auto made = pa::make_application_v9(std::move(store), clock.source());
  pv::require(std::holds_alternative<pa::ApplicationV9>(made.result),
              "the application did not open");
  return std::get<pa::ApplicationV9>(std::move(made.result));
}

// Kind 2, with the stamp before the blob.
inline Bytes init_chain_payload(std::uint64_t genesis_timestamp) {
  const auto identity = v9::chain_id(fixture::trace_genesis());
  pv::require(identity.has_value(), "the trace genesis has a chain identity");
  Bytes payload(identity->begin(), identity->end());
  append_u64(payload, 1);
  append_u64(payload, genesis_timestamp);
  append_blob(payload, kAppStateV9);
  return payload;
}

// Kinds 5 and 6.
inline Bytes block_payload(std::uint64_t height, std::uint64_t timestamp,
                           std::span<const Bytes> transactions) {
  Bytes payload;
  append_u64(payload, height);
  append_u64(payload, timestamp);
  append_transactions(payload, transactions);
  return payload;
}

inline Bytes transaction_payload(std::span<const std::uint8_t> transaction) {
  Bytes payload;
  append_blob(payload, transaction);
  return payload;
}

void check_encoder();
void check_over_a_socket(const pv::Values& values,
                         const std::filesystem::path& directory);

}  // namespace transport_v9_tests

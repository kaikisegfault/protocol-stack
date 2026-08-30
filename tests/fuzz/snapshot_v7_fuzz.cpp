// The version-seven snapshot decoder over arbitrary bytes.
//
// The decoder is the node's whole untrusted surface for a restore: a snapshot
// arrives as a file, and nothing about the process that wrote it is guaranteed.
// What this asserts beyond "does not crash" is the three properties a restore
// rests on.
//
// **Decoding is total**: it answers an error rather than throwing, reading out
// of bounds, or depending on how the bytes were produced. **Decoding is
// deterministic**, so two nodes handed identical bytes reach identical answers.
// And **anything it accepts re-encodes to exactly the bytes it came from**,
// which is what makes the payload canonical — a decoder that tolerated a second
// representation of one state would fail here rather than at whatever later step
// first noticed two snapshots of one height.

#include "protocol/storage/snapshot_v7.hpp"

#include "protocol/v1/crypto.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <span>
#include <string_view>
#include <variant>

namespace ps = protocol::storage;
namespace v7 = protocol::v7;

namespace {

void require(bool condition) {
  if (!condition) std::abort();
}

// A genesis ledger: height zero, no accounts, and the fourteen fixed entries
// every chain opens with. It is the smallest state a conforming chain has, which
// makes it the seed whose neighbourhood is worth exploring.
const v7::Ledger& seed_ledger() {
  static const v7::Ledger ledger = [] {
    v7::Genesis genesis;
    genesis.network_id = 7;
    genesis.supply_limit = 5'699'395'010'000'000'000;
    genesis.fixed_transfer_fee = 1'000;
    genesis.manifest_digest.fill(0x11);
    genesis.verifier_key.fill(0x55);
    auto opened = v7::open_ledger(genesis);
    require(opened.has_value());
    return *opened;
  }();
  return ledger;
}

const ps::SnapshotParametersV7& seed_parameters() {
  static const auto parameters = ps::snapshot_parameters(seed_ledger());
  return parameters;
}

const v7::Bytes& seed_payload() {
  static const v7::Bytes payload = [] {
    auto encoded = ps::encode_snapshot_v7(seed_ledger());
    require(std::holds_alternative<ps::EncodedSnapshotV7>(encoded));
    return std::get<ps::EncodedSnapshotV7>(encoded).payload;
  }();
  return payload;
}

void fuzz_payload(std::span<const std::uint8_t> input) {
  auto first = ps::decode_snapshot_v7(input, seed_parameters());
  auto second = ps::decode_snapshot_v7(input, seed_parameters());
  const bool restored = std::holds_alternative<ps::DecodedSnapshotV7>(first);
  require(restored == std::holds_alternative<ps::DecodedSnapshotV7>(second));
  if (!restored) {
    require(std::get<ps::SnapshotV7Error>(first) ==
            std::get<ps::SnapshotV7Error>(second));
    return;
  }
  const auto& decoded = std::get<ps::DecodedSnapshotV7>(first);
  // A restored state is one some sequence of blocks could have produced, and it
  // commits the root the payload claimed.
  require(v7::conservation_failures(decoded.ledger).empty());
  const auto root = v7::ledger_state_root(decoded.ledger);
  require(root.has_value() && *root == decoded.state_root);

  auto reencoded = ps::encode_snapshot_v7(decoded.ledger);
  require(std::holds_alternative<ps::EncodedSnapshotV7>(reencoded));
  const auto& payload = std::get<ps::EncodedSnapshotV7>(reencoded).payload;
  require(payload.size() == input.size());
  require(std::equal(payload.begin(), payload.end(), input.begin()));
}

// Rewrite the trailing digest so a mutated payload is a *different state*
// rather than a corrupted one. Without this every structured mutation stops at
// the digest gate and the value decoders are never reached at all.
//
// The domain label is restated here, and a drift would silently weaken this
// target rather than break it — so `require_reseal_is_accepted` below decodes an
// unmutated resealed payload and aborts if it does not, which turns a silent
// weakening into a loud failure.
constexpr std::string_view kDigestDomain = "protocol-stack:storage:snapshot-v7";
constexpr std::size_t kDigestSize = 32;

void reseal(v7::Bytes& payload) {
  const auto digest = protocol::v1::hash(
      kDigestDomain,
      std::span<const std::uint8_t>{payload.data(), payload.size() - kDigestSize});
  std::copy(digest.begin(), digest.end(), payload.end() - kDigestSize);
}

void require_reseal_is_accepted() {
  auto payload = seed_payload();
  reseal(payload);
  require(std::holds_alternative<ps::DecodedSnapshotV7>(
      ps::decode_snapshot_v7(payload, seed_parameters())));
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data,
                                      std::size_t size) {
  fuzz_payload(std::span<const std::uint8_t>{data, size});

  // The seed must still restore after every input, which is what catches a
  // decoder that left shared state behind.
  fuzz_payload(seed_payload());
  require_reseal_is_accepted();

  // A structured neighbour of a valid payload, resealed so the fuzzer reaches
  // the ordering rules and the value decoders behind the digest.
  if (size >= 2) {
    auto structured = seed_payload();
    const auto index =
        static_cast<std::size_t>(data[0]) % (structured.size() - kDigestSize);
    structured[index] ^= data[size - 1];
    reseal(structured);
    fuzz_payload(structured);
  }
  return 0;
}

// The version-nine snapshot decoder over arbitrary bytes.
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

#include "protocol/storage/snapshot_v9.hpp"

#include "protocol/v1/crypto.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <span>
#include <string_view>
#include <variant>

namespace ps = protocol::storage;
namespace v9 = protocol::v9;

namespace {

void require(bool condition) {
  if (!condition) std::abort();
}

// A genesis ledger: height zero, no accounts, and the sixteen fixed entries
// every chain opens with — version eight's fourteen plus the settlement cursor
// and window zero's month. It is the smallest state a conforming chain has,
// which makes it the seed whose neighbourhood is worth exploring.
const v9::Ledger& seed_ledger() {
  static const v9::Ledger ledger = [] {
    v9::Genesis genesis;
    genesis.network_id = 9;
    genesis.supply_limit = 5'699'395'010'000'000'000;
    genesis.fixed_transfer_fee = 1'000;
    genesis.manifest_digest.fill(0x11);
    genesis.verifier_key.fill(0x55);
    // Version eight's ninth genesis field. It must differ from the verifier key,
    // because the whole reason it is a separate field is that attesting HUB
    // identities should not carry the power to void a machine's uptime.
    genesis.dispute_authority_key.fill(0xD8);
    // Version nine's tenth. It must be inside `calendar-v1`'s accepted range or
    // the genesis is malformed and there is no seed to explore from; this is the
    // trace's own value, so the seed sits on the calendar where a real chain
    // does rather than at the epoch.
    genesis.genesis_timestamp = 1'768'435'200'000;
    auto opened = v9::open_ledger(genesis);
    require(opened.has_value());
    return *opened;
  }();
  return ledger;
}

const ps::SnapshotParametersV9& seed_parameters() {
  static const auto parameters = ps::snapshot_parameters(seed_ledger());
  return parameters;
}

const v9::Bytes& seed_payload() {
  static const v9::Bytes payload = [] {
    auto encoded = ps::encode_snapshot_v9(seed_ledger());
    require(std::holds_alternative<ps::EncodedSnapshotV9>(encoded));
    return std::get<ps::EncodedSnapshotV9>(encoded).payload;
  }();
  return payload;
}

void fuzz_payload(std::span<const std::uint8_t> input) {
  auto first = ps::decode_snapshot_v9(input, seed_parameters());
  auto second = ps::decode_snapshot_v9(input, seed_parameters());
  const bool restored = std::holds_alternative<ps::DecodedSnapshotV9>(first);
  require(restored == std::holds_alternative<ps::DecodedSnapshotV9>(second));
  if (!restored) {
    require(std::get<ps::SnapshotV9Error>(first) ==
            std::get<ps::SnapshotV9Error>(second));
    return;
  }
  const auto& decoded = std::get<ps::DecodedSnapshotV9>(first);
  // A restored state is one some sequence of blocks could have produced, and it
  // commits the root the payload claimed.
  require(v9::conservation_failures(decoded.ledger).empty());
  const auto root = v9::ledger_state_root(decoded.ledger);
  require(root.has_value() && *root == decoded.state_root);

  auto reencoded = ps::encode_snapshot_v9(decoded.ledger);
  require(std::holds_alternative<ps::EncodedSnapshotV9>(reencoded));
  const auto& payload = std::get<ps::EncodedSnapshotV9>(reencoded).payload;
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
constexpr std::string_view kDigestDomain = "protocol-stack:storage:snapshot-v9";
constexpr std::size_t kDigestSize = 32;

void reseal(v9::Bytes& payload) {
  const auto digest = protocol::v1::hash(
      kDigestDomain,
      std::span<const std::uint8_t>{payload.data(), payload.size() - kDigestSize});
  std::copy(digest.begin(), digest.end(), payload.end() - kDigestSize);
}

void require_reseal_is_accepted() {
  auto payload = seed_payload();
  reseal(payload);
  require(std::holds_alternative<ps::DecodedSnapshotV9>(
      ps::decode_snapshot_v9(payload, seed_parameters())));
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

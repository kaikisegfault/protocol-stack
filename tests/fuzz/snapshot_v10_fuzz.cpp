// The version-ten snapshot decoder over arbitrary bytes.
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
// which is what makes the payload canonical.
//
// This is `snapshot_v9_fuzz.cpp`'s counterpart, which ADR 0104's last step must
// keep. **It has two seeds where version nine's has one**, because a genesis
// writes none of the four entries version ten adds, so a neighbourhood of
// genesis alone never reaches their decoders or the retirement rule. The
// second seed is a registry: a hundred machines whose seats met window 1, the
// launch key retired at its assignment, and one registration through a machine.
// It is built through the kernel, with the execution suite's builder and
// recorded signature table, so it is a state a chain reaches rather than one
// this file asserts.
//
// **The registry seed is twenty-seven kilobytes and its root is the cost.** A
// decode computes two roots over about 420 entries. So the seed's own restore
// is checked once, when it is built, and each input explores one seed's
// neighbourhood, chosen by one of its octets, so an input file still reproduces
// exactly. The genesis seed keeps version nine's checks after every input,
// including the one that catches a decoder leaving shared state behind, which
// does not depend on which seed's bytes the decoder last read. Checking both
// seeds after every input made the 512-run smoke take 83 seconds locally
// against a 60-second timeout.

#include "protocol/storage/snapshot_v10.hpp"

#include "../kernel/economy_v10_execution_fixture.hpp"

#include "protocol/v1/crypto.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <span>
#include <string_view>
#include <utility>
#include <variant>

namespace ps = protocol::storage;
namespace v10 = protocol::v10;
namespace fixture = economy_v10_execution;

namespace {

void require(bool condition) {
  if (!condition) std::abort();
}

void fuzz_payload(std::span<const std::uint8_t> input,
                  const ps::SnapshotParametersV10& parameters) {
  auto first = ps::decode_snapshot_v10(input, parameters);
  auto second = ps::decode_snapshot_v10(input, parameters);
  const bool restored = std::holds_alternative<ps::DecodedSnapshotV10>(first);
  require(restored == std::holds_alternative<ps::DecodedSnapshotV10>(second));
  if (!restored) {
    require(std::get<ps::SnapshotV10Error>(first) ==
            std::get<ps::SnapshotV10Error>(second));
    return;
  }
  const auto& decoded = std::get<ps::DecodedSnapshotV10>(first);
  // A restored state is one some sequence of blocks could have produced, and it
  // commits the root the payload claimed.
  require(v10::conservation_failures(decoded.ledger).empty());
  const auto root = v10::ledger_state_root(decoded.ledger);
  require(root.has_value() && *root == decoded.state_root);

  auto reencoded = ps::encode_snapshot_v10(decoded.ledger);
  require(std::holds_alternative<ps::EncodedSnapshotV10>(reencoded));
  const auto& payload = std::get<ps::EncodedSnapshotV10>(reencoded).payload;
  require(payload.size() == input.size());
  require(std::equal(payload.begin(), payload.end(), input.begin()));
}

struct Seed {
  v10::Ledger ledger;
  ps::SnapshotParametersV10 parameters;
  v10::Bytes payload;
};

Seed seed_of(v10::Ledger ledger) {
  Seed seed{std::move(ledger), {}, {}};
  seed.parameters = ps::snapshot_parameters(seed.ledger);
  auto encoded = ps::encode_snapshot_v10(seed.ledger);
  require(std::holds_alternative<ps::EncodedSnapshotV10>(encoded));
  seed.payload = std::get<ps::EncodedSnapshotV10>(std::move(encoded)).payload;
  return seed;
}

// A genesis ledger: height zero, no accounts, and version nine's sixteen fixed
// entries, with the launch key in entry kind 8. It is the smallest state a
// conforming chain has.
const Seed& genesis_seed() {
  static const Seed seed = seed_of(fixture::open_trace_ledger());
  return seed;
}

// Admit and execute one transaction at `height`, which must succeed.
void submit(v10::Ledger& ledger, const fixture::Signatures& signatures,
            std::uint64_t height, const v10::Bytes& raw) {
  ledger.height = height;
  ledger.timestamp = fixture::timestamp_of_height(height);
  const auto verify = signatures.verifier();
  const auto admission = v10::admit(raw, ledger.chain_id, verify);
  require(admission.admitted());
  const auto outcome = v10::execute(ledger, admission.transaction.envelope, verify);
  require(outcome.has_value() && outcome->succeeded());
}

// The population harness in miniature (ADR 0105): one founder sells and
// activates a hundred seats in window 0 and registers a key for each, windows
// 1 to 3 open with every seat fully credited, and the window-1 assignment
// counts a hundred active machines and retires the launch key. One person then
// registers through seat 0's machine, which writes the founder count.
const Seed& registry_seed() {
  static const Seed seed = [] {
    constexpr std::uint32_t kSeats = v10::kLaunchRetirementActiveMachines;
    const auto& founder = fixture::kPopulationFounder;
    fixture::Signatures signatures;
    auto ledger = fixture::open_trace_ledger();
    const fixture::Builder build(signatures, ledger);
    const auto nonce = [&] { return fixture::nonce_of(ledger, founder.escrow()) + 1; };
    const auto until = [&](std::uint64_t height) { return height + fixture::kLifetime; };

    submit(ledger, signatures, 1,
           build.registration(founder, v10::kLaunchAttester, fixture::kLaunchKey,
                              until(1)));
    for (std::uint32_t seat = 0; seat < kSeats; ++seat) {
      submit(ledger, signatures, 2, build.purchase(founder, seat, nonce(), until(2)));
    }
    const auto activation = v10::kCycleBlocks - 10;
    for (std::uint32_t seat = 0; seat < kSeats; ++seat) {
      submit(ledger, signatures, activation,
             build.activation(founder, seat, nonce(), until(activation)));
    }
    for (std::uint32_t seat = 0; seat < kSeats; ++seat) {
      submit(ledger, signatures, activation + 1,
             build.machine_registration(founder, seat, fixture::machine_key(seat),
                                        nonce(), until(activation + 1)));
    }
    for (std::uint64_t window = 1; window <= 3; ++window) {
      ledger.height = window * v10::kCycleBlocks;
      ledger.timestamp = fixture::timestamp_of_height(ledger.height);
      require(v10::open_window(ledger).has_value());
    }
    require(ledger.launch_retired_at == 3 * v10::kCycleBlocks);
    const auto height = 3 * v10::kCycleBlocks + 1;
    submit(ledger, signatures, height,
           build.registration(fixture::person(1), 0, fixture::machine_key(0),
                              until(height)));
    require(ledger.founder_registrations.size() == 1);
    auto built = seed_of(std::move(ledger));
    fuzz_payload(built.payload, built.parameters);
    return built;
  }();
  return seed;
}

// Rewrite the trailing digest so a mutated payload is a *different state*
// rather than a corrupted one. Without this every structured mutation stops at
// the digest gate and the value decoders are never reached at all.
//
// The domain label is restated here, and a drift would silently weaken this
// target rather than break it, so `require_reseal_is_accepted` decodes an
// unmutated resealed payload and aborts if it does not.
constexpr std::string_view kDigestDomain = "protocol-stack:storage:snapshot-v10";
constexpr std::size_t kDigestSize = 32;

void reseal(v10::Bytes& payload) {
  const auto digest = protocol::v1::hash(
      kDigestDomain,
      std::span<const std::uint8_t>{payload.data(), payload.size() - kDigestSize});
  std::copy(digest.begin(), digest.end(), payload.end() - kDigestSize);
}

void require_reseal_is_accepted(const Seed& seed) {
  auto payload = seed.payload;
  reseal(payload);
  require(std::holds_alternative<ps::DecodedSnapshotV10>(
      ps::decode_snapshot_v10(payload, seed.parameters)));
}

// A structured neighbour of a valid payload, resealed so the fuzzer reaches the
// ordering rules and the value decoders behind the digest. The offset is two
// octets of the input, because the registry seed is larger than one octet can
// index, and the third octet's low bit chooses the seed.
void fuzz_neighbour(std::span<const std::uint8_t> input) {
  if (input.size() < 3) return;
  const auto& seed = (input[2] & 1U) != 0 ? registry_seed() : genesis_seed();
  auto structured = seed.payload;
  const auto offset = (static_cast<std::size_t>(input[0]) << 8U) | input[1];
  const auto index = offset % (structured.size() - kDigestSize);
  structured[index] ^= input[input.size() - 1];
  reseal(structured);
  fuzz_payload(structured, seed.parameters);
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data,
                                      std::size_t size) {
  const std::span<const std::uint8_t> input{data, size};
  const auto& genesis = genesis_seed();
  const auto& registry = registry_seed();
  fuzz_payload(input, genesis.parameters);
  fuzz_payload(input, registry.parameters);

  // The seed must still restore after every input, which is what catches a
  // decoder that left shared state behind.
  fuzz_payload(genesis.payload, genesis.parameters);
  require_reseal_is_accepted(genesis);

  fuzz_neighbour(input);
  return 0;
}

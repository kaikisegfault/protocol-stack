// A store seeded from a snapshot, which is how a network begins above height
// zero (ADR 0096).
//
// **A seeded store must be indistinguishable from the store that produced the
// snapshot.** So the payload is taken from a store that executed the recorded
// run's first two blocks. The seeded store must report that head, reopen to it,
// and then execute blocks three to five to the roots the vectors record. That
// last step is the claim that matters: a seeded network's first block is an
// ordinary block against an ordinary head. **The fifth block reads the build
// authority key**, which the payload does not carry and the seeded store takes
// from the genesis its caller presents (ADR 0108).
//
// **A refused seed must leave no file behind**, because a half-written store at
// the path is what a launcher would open next and mistake for a seeded one.
//
// **Inspection must agree with seeding in both directions** (ADR 0097): it
// reports the head a seed creates, and refuses every payload a seed refuses.

#include "sqlite_ledger_v10_fixture.hpp"

#include <span>
#include <string>

namespace sqlite_ledger_v10_tests {
namespace {

v10::Bytes head_payload(const ps::SQLiteLedgerV10& store, const std::string& subject) {
  auto snapshot = store.create_snapshot();
  pv::require(std::holds_alternative<v10::Bytes>(snapshot),
              subject + ": the head has no payload");
  return std::get<v10::Bytes>(std::move(snapshot));
}

void require_refused_seed(const std::filesystem::path& path,
                          std::span<const std::uint8_t> payload,
                          const v10::Genesis& genesis,
                          ps::SQLiteLedgerV10Error expected,
                          const std::string& subject) {
  const bool existed = std::filesystem::exists(path);
  require_store_error(
      ps::seed_sqlite_ledger_v10(path, genesis, payload, trace_verifier()),
      expected, subject);
  pv::require(std::filesystem::exists(path) == existed,
              subject + ": a refused seed changed what is at the path");
}

// Inspecting a payload must report the head a seed from it creates, because a
// launcher writes the engine's genesis from the one and starts on the other.
void require_inspected(std::span<const std::uint8_t> payload,
                       const v10::Genesis& genesis, const pv::Values& values,
                       std::size_t index, const std::string& subject) {
  auto inspected = ps::inspect_seed_v10(genesis, payload);
  pv::require(std::holds_alternative<ps::LedgerHeadV10>(inspected),
              subject + ": the payload was refused");
  const auto head = std::get<ps::LedgerHeadV10>(std::move(inspected));
  const auto label = block_label(index);
  pv::require(fixture::hex(head.state_root) ==
                  recorded(values, label + ".resulting_state_root"),
              subject + ": the inspected root is not the recorded one");
  pv::require(head.ledger.height == recorded_number(values, label + ".height"),
              subject + ": the inspected height is not the recorded one");
  pv::require(head.ledger.timestamp ==
                  recorded_number(values, label + ".timestamp"),
              subject + ": the inspected stamp is not the recorded one");
}

// Every payload a seed refuses, inspection refuses the same way.
void require_refused_inspection(std::span<const std::uint8_t> payload,
                                const v10::Genesis& genesis,
                                const std::string& subject) {
  const auto inspected = ps::inspect_seed_v10(genesis, payload);
  pv::require(std::holds_alternative<ps::SQLiteLedgerV10Error>(inspected) &&
                  std::get<ps::SQLiteLedgerV10Error>(inspected) ==
                      ps::SQLiteLedgerV10Error::invalid_snapshot,
              subject + ": inspection did not refuse it as invalid_snapshot");
}

}  // namespace

void check_seeding(const pv::Values& values,
                   const std::filesystem::path& directory) {
  const auto genesis = fixture::trace_genesis();
  const auto source_path = directory / "seed-source.sqlite";
  const auto seeded_path = directory / "seeded.sqlite";
  constexpr std::size_t kSeedBlocks = 2;

  v10::Bytes payload;
  v10::Bytes genesis_payload;
  {
    auto source = require_store(
        ps::create_sqlite_ledger_v10(source_path, genesis, trace_verifier()),
        "the seed's source store");
    genesis_payload = head_payload(source, "the source at genesis");
    for (std::size_t index = 0; index < kSeedBlocks; ++index) {
      apply_and_compare(source, values, index);
    }
    payload = head_payload(source, "the source after two blocks");
  }

  require_inspected(payload, genesis, values, kSeedBlocks - 1,
                    "the source's head, inspected");
  {
    auto seeded = require_store(
        ps::seed_sqlite_ledger_v10(seeded_path, genesis, payload, trace_verifier()),
        "a seed from the source's head");
    require_head(seeded, values, kSeedBlocks - 1, "the seeded head");
  }
  {
    auto reopened = require_store(
        ps::open_sqlite_ledger_v10(seeded_path, genesis, trace_verifier()),
        "the seeded store reopened");
    require_head(reopened, values, kSeedBlocks - 1, "the reopened seeded head");
    for (std::size_t index = kSeedBlocks; index < kContiguousBlocks; ++index) {
      apply_and_compare(reopened, values, index);
    }
    require_head(reopened, values, kContiguousBlocks - 1,
                 "the seeded store after the run's remaining blocks");
  }

  require_refused_seed(seeded_path, payload, genesis,
                       ps::SQLiteLedgerV10Error::path_already_exists,
                       "a seed onto an existing store");
  // A store at the path is no reason to refuse an inspection: a launcher
  // restarting a seeded network inspects the payload its stores began from.
  require_inspected(payload, genesis, values, kSeedBlocks - 1,
                    "the head inspected beside its seeded store");
  require_refused_seed(directory / "seeded-at-genesis.sqlite", genesis_payload,
                       genesis, ps::SQLiteLedgerV10Error::invalid_snapshot,
                       "a seed at height zero, which is a genesis");
  require_refused_inspection(genesis_payload, genesis,
                             "a height-zero payload, inspected");

  auto tampered = payload;
  tampered[tampered.size() / 2] ^= 0x01U;
  require_refused_seed(directory / "seeded-tampered.sqlite", tampered, genesis,
                       ps::SQLiteLedgerV10Error::invalid_snapshot,
                       "a seed whose payload was altered");
  require_refused_inspection(tampered, genesis, "an altered payload, inspected");

  // The same state offered to another chain: the snapshot names its chain, so
  // it must not seed a store under a different genesis.
  auto foreign = genesis;
  foreign.network_id += 1;
  require_refused_seed(directory / "seeded-foreign.sqlite", payload, foreign,
                       ps::SQLiteLedgerV10Error::invalid_snapshot,
                       "a seed under another chain's genesis");
  require_refused_inspection(payload, foreign,
                             "a payload inspected under another chain's genesis");

  // **The same state under another build authority key**, which is version
  // ten's parameter. The key changes the chain identity the payload names, so
  // the payload belongs to a different chain and must not seed this one: a
  // network seeded under another authority would admit the machines that
  // authority attests.
  auto reattested = genesis;
  reattested.build_authority_key[0] ^= 0xFFU;
  require_refused_seed(directory / "seeded-reattested.sqlite", payload, reattested,
                       ps::SQLiteLedgerV10Error::invalid_snapshot,
                       "a seed under another build authority key");
  require_refused_inspection(payload, reattested,
                             "a payload inspected under another build authority key");
}

}  // namespace sqlite_ledger_v10_tests

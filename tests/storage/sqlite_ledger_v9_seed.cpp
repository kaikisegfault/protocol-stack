// A store seeded from a snapshot, which is how a network begins above height
// zero (ADR 0096).
//
// **A seeded store must be indistinguishable from the store that produced the
// snapshot.** So the payload is taken from a store that executed the recorded
// run's first two blocks. The seeded store must report that head, reopen to it,
// and then execute blocks three and four to the roots the vectors record. That
// last step is the claim that matters: a seeded network's first block is an
// ordinary block against an ordinary head.
//
// **A refused seed must leave no file behind**, because a half-written store at
// the path is what a launcher would open next and mistake for a seeded one.

#include "sqlite_ledger_v9_fixture.hpp"

#include <string>

namespace sqlite_ledger_v9_tests {
namespace {

v9::Bytes head_payload(const ps::SQLiteLedgerV9& store, const std::string& subject) {
  auto snapshot = store.create_snapshot();
  pv::require(std::holds_alternative<v9::Bytes>(snapshot),
              subject + ": the head has no payload");
  return std::get<v9::Bytes>(std::move(snapshot));
}

void require_refused_seed(const std::filesystem::path& path,
                          std::span<const std::uint8_t> payload,
                          const v9::Genesis& genesis,
                          ps::SQLiteLedgerV9Error expected,
                          const std::string& subject) {
  const bool existed = std::filesystem::exists(path);
  require_store_error(
      ps::seed_sqlite_ledger_v9(path, genesis, payload, trace_verifier()),
      expected, subject);
  pv::require(std::filesystem::exists(path) == existed,
              subject + ": a refused seed changed what is at the path");
}

}  // namespace

void check_seeding(const pv::Values& values,
                   const std::filesystem::path& directory) {
  const auto genesis = fixture::trace_genesis();
  const auto source_path = directory / "seed-source.sqlite";
  const auto seeded_path = directory / "seeded.sqlite";
  constexpr std::size_t kSeedBlocks = 2;

  v9::Bytes payload;
  v9::Bytes genesis_payload;
  {
    auto source = require_store(
        ps::create_sqlite_ledger_v9(source_path, genesis, trace_verifier()),
        "the seed's source store");
    genesis_payload = head_payload(source, "the source at genesis");
    for (std::size_t index = 0; index < kSeedBlocks; ++index) {
      apply_and_compare(source, values, index);
    }
    payload = head_payload(source, "the source after two blocks");
  }

  {
    auto seeded = require_store(
        ps::seed_sqlite_ledger_v9(seeded_path, genesis, payload, trace_verifier()),
        "a seed from the source's head");
    require_head(seeded, values, kSeedBlocks - 1, "the seeded head");
  }
  {
    auto reopened = require_store(
        ps::open_sqlite_ledger_v9(seeded_path, genesis, trace_verifier()),
        "the seeded store reopened");
    require_head(reopened, values, kSeedBlocks - 1, "the reopened seeded head");
    for (std::size_t index = kSeedBlocks; index < kContiguousBlocks; ++index) {
      apply_and_compare(reopened, values, index);
    }
    require_head(reopened, values, kContiguousBlocks - 1,
                 "the seeded store after the run's remaining blocks");
  }

  require_refused_seed(seeded_path, payload, genesis,
                       ps::SQLiteLedgerV9Error::path_already_exists,
                       "a seed onto an existing store");
  require_refused_seed(directory / "seeded-at-genesis.sqlite", genesis_payload,
                       genesis, ps::SQLiteLedgerV9Error::invalid_snapshot,
                       "a seed at height zero, which is a genesis");

  auto tampered = payload;
  tampered[tampered.size() / 2] ^= 0x01U;
  require_refused_seed(directory / "seeded-tampered.sqlite", tampered, genesis,
                       ps::SQLiteLedgerV9Error::invalid_snapshot,
                       "a seed whose payload was altered");

  // The same state offered to another chain: the snapshot names its chain, so
  // it must not seed a store under a different genesis.
  auto foreign = genesis;
  foreign.network_id += 1;
  require_refused_seed(directory / "seeded-foreign.sqlite", payload, foreign,
                       ps::SQLiteLedgerV9Error::invalid_snapshot,
                       "a seed under another chain's genesis");
}

}  // namespace sqlite_ledger_v9_tests

#pragma once

// What the version-ten store's test translation units share: the recorded run
// they replay, the verifier it was recorded under, and the assertions every case
// is written in terms of.
//
// The run and the signature table are built once and held, because building one
// runs the trace and every suite needs the same bytes.

#include "protocol/storage/sqlite_ledger_v10.hpp"

#include "../kernel/economy_v10_execution_fixture.hpp"

#include <sqlite3.h>

#include <filesystem>
#include <string>
#include <variant>

namespace sqlite_ledger_v10_tests {

namespace ps = protocol::storage;
namespace v10 = protocol::v10;
namespace pv = protocol_vectors;
namespace fixture = economy_v10_execution;

// **The whole `restart` run, rather than a prefix of a longer chain.** The
// recorded version-ten chain jumps to the activation height, and a store has no
// operation that does that, because a skipped height is a stamp C2 never
// compared and, once a seat is in scope, an audit that was owed and never
// performed. The run was recorded for exactly this suite and the layers above
// it (M4.3h-1). **Its fifth block is version ten's**: both machines register
// through kind 23, whose attestation verifies against the build authority key,
// so a store that reopened without it would refuse that block alone.
constexpr std::size_t kContiguousBlocks = 5;

inline std::string error_name(ps::SQLiteLedgerV10Error error) {
  switch (error) {
    case ps::SQLiteLedgerV10Error::invalid_genesis: return "invalid_genesis";
    case ps::SQLiteLedgerV10Error::invalid_path: return "invalid_path";
    case ps::SQLiteLedgerV10Error::path_already_exists: return "path_already_exists";
    case ps::SQLiteLedgerV10Error::path_not_found: return "path_not_found";
    case ps::SQLiteLedgerV10Error::lock_unavailable: return "lock_unavailable";
    case ps::SQLiteLedgerV10Error::configuration_mismatch: return "configuration_mismatch";
    case ps::SQLiteLedgerV10Error::integrity_failure: return "integrity_failure";
    case ps::SQLiteLedgerV10Error::schema_mismatch: return "schema_mismatch";
    case ps::SQLiteLedgerV10Error::genesis_mismatch: return "genesis_mismatch";
    case ps::SQLiteLedgerV10Error::state_mismatch: return "state_mismatch";
    case ps::SQLiteLedgerV10Error::storage_failure: return "storage_failure";
    case ps::SQLiteLedgerV10Error::invalid_snapshot: return "invalid_snapshot";
  }
  return "unknown";
}

inline ps::SQLiteLedgerV10 require_store(ps::SQLiteLedgerV10Result result,
                                        const std::string& subject) {
  if (std::holds_alternative<ps::SQLiteLedgerV10Error>(result.result)) {
    pv::require(false, subject + ": " + error_name(std::get<ps::SQLiteLedgerV10Error>(
                                            result.result)));
  }
  return std::get<ps::SQLiteLedgerV10>(std::move(result.result));
}

inline void require_store_error(ps::SQLiteLedgerV10Result result,
                                ps::SQLiteLedgerV10Error expected,
                                const std::string& subject) {
  pv::require(std::holds_alternative<ps::SQLiteLedgerV10Error>(result.result),
              subject + ": the store opened");
  const auto actual = std::get<ps::SQLiteLedgerV10Error>(result.result);
  pv::require(actual == expected, subject + ": expected " + error_name(expected) +
                                      ", got " + error_name(actual));
}

inline const fixture::Restart& restart_run() {
  static const fixture::Restart scenario = [] {
    fixture::Signatures signatures;
    return fixture::restart_scenario(signatures);
  }();
  return scenario;
}

// The verifier the recorded run was produced under. The store never chooses a
// verification rule, exactly as the kernel does not: a recorded stand-in table is
// what lets the run exist at all.
inline v10::SignatureVerifier trace_verifier() {
  static const fixture::Signatures signatures = [] {
    fixture::Signatures table;
    (void)fixture::restart_scenario(table);
    return table;
  }();
  return signatures.verifier();
}

inline std::string recorded(const pv::Values& values, const std::string& key) {
  const auto found = values.find(key);
  pv::require(found != values.end(), "the vectors record no " + key);
  return found->second;
}

inline std::uint64_t recorded_number(const pv::Values& values,
                                     const std::string& key) {
  return std::stoull(recorded(values, key));
}

inline std::string block_label(std::size_t index) {
  return "restart.block" + std::to_string(index);
}

// Apply one block and compare it against the vectors, not against the kernel.
// **The height and the stamp are the model's**, read from the vectors rather
// than from the C++ trace, so the only thing this suite takes from the trace is
// the raw bytes it offers.
inline void apply_and_compare(ps::SQLiteLedgerV10& store, const pv::Values& values,
                              std::size_t index) {
  const auto label = block_label(index);
  const auto height = recorded_number(values, label + ".height");
  const auto timestamp = recorded_number(values, label + ".timestamp");
  auto applied =
      store.apply_block(height, timestamp, restart_run().block_inputs[index]);
  if (std::holds_alternative<ps::SQLiteLedgerV10Error>(applied)) {
    pv::require(false, label + ": " + error_name(std::get<ps::SQLiteLedgerV10Error>(
                                          applied)));
  }
  pv::require(std::holds_alternative<ps::BlockCommitV10>(applied),
              label + ": the block was rejected");
  const auto commit = std::get<ps::BlockCommitV10>(applied);
  pv::require(commit.height == height, label + ": committed at the wrong height");
  pv::require(commit.timestamp == timestamp,
              label + ": committed at the wrong timestamp");
  pv::require(fixture::hex(commit.resulting_state_root) ==
                  recorded(values, label + ".resulting_state_root"),
              label + ": the durable root is not the recorded one");
  pv::require(fixture::hex(commit.block_id) == recorded(values, label + ".block_id"),
              label + ": the block identifier is not the recorded one");
  pv::require(fixture::hex(commit.transaction_root) ==
                  recorded(values, label + ".transaction_root"),
              label + ": the transaction root is not the recorded one");
  pv::require(commit.transaction_count ==
                  recorded_number(values, label + ".admitted_count"),
              label + ": the admitted count is not the recorded one");
}

// **The head's stamp is checked beside its root**, although the root commits to
// it. A root proves agreement without showing the value, and one question a
// restart raises is precisely which stamp came back.
inline void require_head(const ps::SQLiteLedgerV10& store, const pv::Values& values,
                         std::size_t index, const std::string& subject) {
  auto head = store.read_head();
  pv::require(std::holds_alternative<ps::LedgerHeadV10>(head),
              subject + ": the head is unreadable");
  const auto value = std::get<ps::LedgerHeadV10>(std::move(head));
  const auto label = block_label(index);
  pv::require(fixture::hex(value.state_root) ==
                  recorded(values, label + ".resulting_state_root"),
              subject + ": the head is not at the recorded root");
  pv::require(value.ledger.height == recorded_number(values, label + ".height"),
              subject + ": the head is not at the recorded height");
  pv::require(value.ledger.timestamp ==
                  recorded_number(values, label + ".timestamp"),
              subject + ": the head is not at the recorded stamp");
  pv::require(v10::conservation_failures(value.ledger).empty(),
              subject + ": a restored head must be conserved");
  // No root commits to the build authority key, so the root comparison above
  // says nothing about it, and the fifth block is the only one that reads it.
  pv::require(value.ledger.build_authority_key == fixture::kBuildAuthorityKey,
              subject + ": the head lost the build authority key");
  const auto derived = v10::ledger_state_root(value.ledger);
  pv::require(derived.has_value() && *derived == value.state_root,
              subject + ": the head does not project to its own root");
}

void check_restart_equivalence(const pv::Values& values,
                               const std::filesystem::path& directory);
void check_uninterrupted(const pv::Values& values,
                         const std::filesystem::path& directory);
void check_refusals(const pv::Values& values,
                    const std::filesystem::path& directory);
void check_tampering(const pv::Values& values,
                     const std::filesystem::path& directory);
void check_column_bounds(const pv::Values& values,
                         const std::filesystem::path& directory);
void check_page_corruption(const pv::Values& values,
                           const std::filesystem::path& directory);
void check_seeding(const pv::Values& values,
                   const std::filesystem::path& directory);

}  // namespace sqlite_ledger_v10_tests

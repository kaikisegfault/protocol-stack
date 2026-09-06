#pragma once

// What the version-eight store's test translation units share: the recorded
// scenario they replay, the verifier it was recorded under, and the two
// assertions every case is written in terms of.
//
// The scenario and the signature table are built once and held, because building
// one runs the whole trace and both halves of the suite need the same bytes.

#include "protocol/storage/sqlite_ledger_v8.hpp"

#include "../kernel/economy_v8_execution_fixture.hpp"

#include <sqlite3.h>

#include <filesystem>
#include <string>
#include <variant>

namespace sqlite_ledger_v8_tests {

namespace ps = protocol::storage;
namespace v8 = protocol::v8;
namespace pv = protocol_vectors;
namespace fixture = economy_v8_execution;

// The four contiguous blocks. Block 4 of the scenario jumps to height
// 1,152,000: the trace's `advance_to` sets the height rather than executing the
// gap, and a
// store has no operation that does that. **Under version eight it could not
// honestly be given one** — a height that is skipped is an audit that was owed
// and never performed, so a store that could jump would be a store that could
// leave consensus.
constexpr std::size_t kContiguousBlocks = 4;

inline std::string error_name(ps::SQLiteLedgerV8Error error) {
  switch (error) {
    case ps::SQLiteLedgerV8Error::invalid_genesis: return "invalid_genesis";
    case ps::SQLiteLedgerV8Error::invalid_path: return "invalid_path";
    case ps::SQLiteLedgerV8Error::path_already_exists: return "path_already_exists";
    case ps::SQLiteLedgerV8Error::path_not_found: return "path_not_found";
    case ps::SQLiteLedgerV8Error::lock_unavailable: return "lock_unavailable";
    case ps::SQLiteLedgerV8Error::configuration_mismatch: return "configuration_mismatch";
    case ps::SQLiteLedgerV8Error::integrity_failure: return "integrity_failure";
    case ps::SQLiteLedgerV8Error::schema_mismatch: return "schema_mismatch";
    case ps::SQLiteLedgerV8Error::genesis_mismatch: return "genesis_mismatch";
    case ps::SQLiteLedgerV8Error::state_mismatch: return "state_mismatch";
    case ps::SQLiteLedgerV8Error::storage_failure: return "storage_failure";
    case ps::SQLiteLedgerV8Error::invalid_snapshot: return "invalid_snapshot";
  }
  return "unknown";
}

inline ps::SQLiteLedgerV8 require_store(ps::SQLiteLedgerV8Result result,
                                 const std::string& subject) {
  if (std::holds_alternative<ps::SQLiteLedgerV8Error>(result.result)) {
    pv::require(false, subject + ": " + error_name(std::get<ps::SQLiteLedgerV8Error>(
                                            result.result)));
  }
  return std::get<ps::SQLiteLedgerV8>(std::move(result.result));
}

inline void require_store_error(ps::SQLiteLedgerV8Result result,
                         ps::SQLiteLedgerV8Error expected,
                         const std::string& subject) {
  pv::require(std::holds_alternative<ps::SQLiteLedgerV8Error>(result.result),
              subject + ": the store opened");
  const auto actual = std::get<ps::SQLiteLedgerV8Error>(result.result);
  pv::require(actual == expected, subject + ": expected " + error_name(expected) +
                                      ", got " + error_name(actual));
}

inline const fixture::Scenario& carried_scenario() {
  static const fixture::Scenario scenario = [] {
    fixture::Signatures signatures;
    return fixture::carried_scenario(signatures);
  }();
  return scenario;
}

// The verifier the recorded trace was produced under. The store never chooses a
// verification rule, exactly as the kernel does not: a recorded stand-in table is
// what lets the scenarios exist at all.
inline v8::SignatureVerifier trace_verifier() {
  static const fixture::Signatures signatures = [] {
    fixture::Signatures table;
    (void)fixture::carried_scenario(table);
    return table;
  }();
  return signatures.verifier();
}

inline std::string recorded(const pv::Values& values, const std::string& key) {
  const auto found = values.find(key);
  pv::require(found != values.end(), "the vectors record no " + key);
  return found->second;
}

// Apply one block and compare it against the vectors, not against the kernel.
inline void apply_and_compare(ps::SQLiteLedgerV8& store, const pv::Values& values,
                       std::size_t index) {
  const auto& scenario = carried_scenario();
  const auto& recorded_block = scenario.blocks[index];
  auto applied = store.apply_block(recorded_block.height,
                                   scenario.block_inputs[index]);
  const auto label = "carried.block" + std::to_string(index);
  if (std::holds_alternative<ps::SQLiteLedgerV8Error>(applied)) {
    pv::require(false, label + ": " + error_name(std::get<ps::SQLiteLedgerV8Error>(
                                          applied)));
  }
  pv::require(std::holds_alternative<ps::BlockCommitV8>(applied),
              label + ": the block was rejected");
  const auto commit = std::get<ps::BlockCommitV8>(applied);
  pv::require(commit.height == recorded_block.height,
              label + ": committed at the wrong height");
  pv::require(fixture::hex(commit.resulting_state_root) ==
                  recorded(values, label + ".resulting_state_root"),
              label + ": the durable root is not the recorded one");
  pv::require(fixture::hex(commit.block_id) == recorded(values, label + ".block_id"),
              label + ": the block identifier is not the recorded one");
  pv::require(fixture::hex(commit.transaction_root) ==
                  recorded(values, label + ".transaction_root"),
              label + ": the transaction root is not the recorded one");
  pv::require(commit.transaction_count ==
                  std::stoull(recorded(values, label + ".admitted_count")),
              label + ": the admitted count is not the recorded one");
}

inline void require_head(const ps::SQLiteLedgerV8& store, const pv::Values& values,
                  std::size_t index, const std::string& subject) {
  auto head = store.read_head();
  pv::require(std::holds_alternative<ps::LedgerHeadV8>(head),
              subject + ": the head is unreadable");
  const auto value = std::get<ps::LedgerHeadV8>(std::move(head));
  const auto label = "carried.block" + std::to_string(index);
  pv::require(fixture::hex(value.state_root) ==
                  recorded(values, label + ".resulting_state_root"),
              subject + ": the head is not at the recorded root");
  pv::require(v8::conservation_failures(value.ledger).empty(),
              subject + ": a restored head must be conserved");
  const auto derived = v8::ledger_state_root(value.ledger);
  pv::require(derived.has_value() && *derived == value.state_root,
              subject + ": the head does not project to its own root");
}

void check_restart_equivalence(const pv::Values& values,
                               const std::filesystem::path& directory);
void check_uninterrupted(const pv::Values& values,
                         const std::filesystem::path& directory);
void check_refusals(const std::filesystem::path& directory);
void check_tampering(const pv::Values& values,
                     const std::filesystem::path& directory);
void check_column_bounds(const pv::Values& values,
                         const std::filesystem::path& directory);
void check_page_corruption(const pv::Values& values,
                           const std::filesystem::path& directory);

}  // namespace sqlite_ledger_v8_tests

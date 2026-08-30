// The version-seven snapshot against the five recorded execution scenarios.
//
// **The evidence is a third source rather than a second opinion of the
// encoder.** Each scenario's final ledger is snapshotted, restored, and required
// to reproduce that scenario's *recorded* `final_state_root` from
// `test-vectors/economy-transition-v7-execution.txt` — a figure this module does
// not choose, produced by a model that knows nothing about snapshots.
//
// A round trip that only compared the restore against the encoder would pass for
// a matched pair of mistakes. Comparing against the recorded root cannot.

#include "snapshot_v7_fixture.hpp"

#include <span>
#include <utility>
#include <variant>

namespace snapshot_v7_tests {
namespace {

v7::Bytes encoded_of(const v7::Ledger& ledger, const std::string& name,
                     v7::Hash& root) {
  auto encoded = ps::encode_snapshot_v7(ledger);
  pv::require(std::holds_alternative<ps::EncodedSnapshotV7>(encoded),
              name + ": the final ledger must encode");
  auto value = std::get<ps::EncodedSnapshotV7>(std::move(encoded));
  root = value.state_root;
  return std::move(value.payload);
}

// One empty block advances the height and commits the empty transaction root, so
// running one on the original and on the restored ledger asks the only question
// a matching root cannot answer: whether what came back still executes.
void check_still_executes(const v7::Ledger& original, const v7::Ledger& restored,
                          const std::string& name) {
  auto left = original;
  auto right = restored;
  const auto verify = v7::ed25519_verifier();
  const auto first = v7::execute_block(left, {}, verify);
  const auto second = v7::execute_block(right, {}, verify);
  pv::require(first.has_value() && second.has_value(),
              name + ": a restored ledger must execute the next block");
  pv::require(first->block_id == second->block_id,
              name + ": the next block differs after a restore");
  pv::require(first->resulting_state_root == second->resulting_state_root,
              name + ": the next state root differs after a restore");
}

// The property that makes the payload-root gate unreachable through today's
// decoders: the rebuild is lossless, so the payload's entry list and the
// restored ledger's own projection are the same bytes. Asserting it is what
// turns "the gate never fires" into a checked fact rather than an assumption.
void check_projection_is_lossless(const v7::Ledger& restored,
                                  const Payload& payload,
                                  const std::string& name) {
  auto projected = v7::economy_entries(restored);
  std::sort(projected.begin(), projected.end(),
            [](const v7::EconomyEntry& left, const v7::EconomyEntry& right) {
              return left.key < right.key;
            });
  pv::require(projected.size() == payload.economy.size(),
              name + ": the restored projection lost or gained an entry");
  for (std::size_t index = 0; index < projected.size(); ++index) {
    pv::require(projected[index].key == payload.economy[index].key &&
                    projected[index].value == payload.economy[index].value,
                name + ": the restored projection rewrote an entry");
  }
}

std::uint64_t check_scenario(const pv::Values& values,
                             fixture::Scenario (*build)(fixture::Signatures&),
                             const std::string& name) {
  fixture::Signatures signatures;
  const auto scenario = build(signatures);
  const auto& ledger = scenario.ledger;

  v7::Hash root{};
  const auto raw = encoded_of(ledger, name, root);

  // The builder the refusals are constructed with, checked against the module
  // before any test uses it to build a refusal.
  const auto payload = payload_of(ledger);
  pv::require(payload.encode() == raw,
              name + ": the test's payload builder and the encoder disagree");

  const auto recorded = values.find(name + ".final_state_root");
  pv::require(recorded != values.end(),
              "the vectors record no " + name + ".final_state_root");
  pv::require(fixture::hex(root) == recorded->second,
              name + ": the snapshot commits " + fixture::hex(root) +
                  ", the vectors record " + recorded->second);

  const auto parameters = ps::snapshot_parameters(ledger);
  auto decoded = ps::decode_snapshot_v7(raw, parameters);
  pv::require(std::holds_alternative<ps::DecodedSnapshotV7>(decoded),
              name + ": a valid snapshot must restore");
  // Bound by value rather than by reference into the variant: the hosted matrix
  // runs a GCC whose `-Wdangling-reference` does not exist on this machine, and
  // a reference into a `std::get` result is exactly what it objects to.
  const v7::Ledger restored =
      std::get<ps::DecodedSnapshotV7>(std::move(decoded)).ledger;

  const auto restored_root = v7::ledger_state_root(restored);
  pv::require(restored_root.has_value(), name + ": a restored ledger commits a root");
  pv::require(fixture::hex(*restored_root) == recorded->second,
              name + ": the restored ledger does not reproduce the recorded root");
  pv::require(v7::conservation_failures(restored).empty(),
              name + ": a restored state must be conserved");

  // `assigned_permissions` is re-derived from the assignment records rather than
  // read, and the channel identity is stated over exactly this figure.
  pv::require(restored.assigned_permissions == ledger.assigned_permissions,
              name + ": the re-derived permission count differs");

  auto again = ps::encode_snapshot_v7(restored);
  pv::require(std::holds_alternative<ps::EncodedSnapshotV7>(again),
              name + ": a restored ledger must re-encode");
  pv::require(std::get<ps::EncodedSnapshotV7>(again).payload == raw,
              name + ": a restore and a re-encode are not the identity");

  check_projection_is_lossless(restored, payload, name);
  check_still_executes(ledger, restored, name);
  return ledger.assigned_permissions;
}

}  // namespace

void verify_round_trips(const pv::Values& values) {
  const std::array<std::pair<fixture::Scenario (*)(fixture::Signatures&),
                             const char*>,
                   5>
      scenarios{{
          {fixture::pool_scenario, "pool"},
          {fixture::boundary_scenario, "boundary"},
          {fixture::permanence_scenario, "permanence"},
          {fixture::carried_scenario, "carried"},
          {fixture::referral_scenario, "referral"},
      }};
  std::size_t with_permissions = 0;
  for (const auto& [build, name] : scenarios) {
    if (check_scenario(values, build, name) != 0) ++with_permissions;
  }
  // A re-derivation checked only against states that assigned nothing would hold
  // forever and establish nothing.
  pv::require(with_permissions >= 3,
              "at least three scenarios must have assigned a permission");
}

}  // namespace snapshot_v7_tests

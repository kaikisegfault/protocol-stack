// The version-eight snapshot against the four recorded execution scenarios.
//
// **The evidence is a third source rather than a second opinion of the
// encoder.** Each scenario's final ledger is snapshotted, restored, and required
// to reproduce that scenario's *recorded* `final_state_root` from
// `test-vectors/economy-transition-v8-execution.txt` — a figure this module does
// not choose, produced by a model that knows nothing about snapshots.
//
// A round trip that only compared the restore against the encoder would pass for
// a matched pair of mistakes. Comparing against the recorded root cannot.

#include "snapshot_v8_fixture.hpp"

#include <span>
#include <utility>
#include <variant>

namespace snapshot_v8_tests {
namespace {

v8::Bytes encoded_of(const v8::Ledger& ledger, const std::string& name,
                     v8::Hash& root) {
  auto encoded = ps::encode_snapshot_v8(ledger);
  pv::require(std::holds_alternative<ps::EncodedSnapshotV8>(encoded),
              name + ": the final ledger must encode");
  auto value = std::get<ps::EncodedSnapshotV8>(std::move(encoded));
  root = value.state_root;
  return std::move(value.payload);
}

// One empty block advances the height and commits the empty transaction root, so
// running one on the original and on the restored ledger asks the only question
// a matching root cannot answer: whether what came back still executes.
//
// **Under version eight an empty block is not an idle one.** It runs the issue
// step over every in-scope seat and the expiry step over every challenge whose
// deadline has arrived, so this also asks whether the restored uptime map is the
// one the pipeline keeps writing to.
void check_still_executes(const v8::Ledger& original, const v8::Ledger& restored,
                          const std::string& name) {
  auto left = original;
  auto right = restored;
  const auto verify = v8::ed25519_verifier();
  const auto first = v8::execute_block(left, {}, verify);
  const auto second = v8::execute_block(right, {}, verify);
  pv::require(first.has_value() && second.has_value(),
              name + ": a restored ledger must execute the next block");
  pv::require(first->block_id == second->block_id,
              name + ": the next block differs after a restore");
  pv::require(first->resulting_state_root == second->resulting_state_root,
              name + ": the next state root differs after a restore");
}

// The property that keeps the payload-root gate quiet: the rebuild is lossless,
// so the payload's entry list and the restored ledger's own projection are the
// same bytes. Asserting it turns "the gate never fires" into a checked fact
// rather than an assumption — and the gate itself is not decoration, because a
// probe that removes the channel-index bound admits an entry the ledger cannot
// hold and that gate is the one that refuses it.
void check_projection_is_lossless(const v8::Ledger& restored,
                                  const Payload& payload,
                                  const std::string& name) {
  auto projected = v8::economy_entries(restored);
  std::sort(projected.begin(), projected.end(),
            [](const v8::EconomyEntry& left, const v8::EconomyEntry& right) {
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

// What a scenario contributed, so `verify_round_trips` can require that the
// evidence actually covers the surfaces the checks are about.
struct Counted {
  std::uint64_t assigned_permissions = 0;
  std::size_t uptime_entries = 0;
};

Counted check_scenario(const pv::Values& values,
                       fixture::Scenario (*build)(fixture::Signatures&),
                       const std::string& name) {
  fixture::Signatures signatures;
  const auto scenario = build(signatures);
  const auto& ledger = scenario.ledger;

  v8::Hash root{};
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
  auto decoded = ps::decode_snapshot_v8(raw, parameters);
  pv::require(std::holds_alternative<ps::DecodedSnapshotV8>(decoded),
              name + ": a valid snapshot must restore");
  // Bound by value rather than by reference into the variant: the hosted matrix
  // runs a GCC whose `-Wdangling-reference` does not exist on this machine, and
  // a reference into a `std::get` result is exactly what it objects to.
  const v8::Ledger restored =
      std::get<ps::DecodedSnapshotV8>(std::move(decoded)).ledger;

  const auto restored_root = v8::ledger_state_root(restored);
  pv::require(restored_root.has_value(), name + ": a restored ledger commits a root");
  pv::require(fixture::hex(*restored_root) == recorded->second,
              name + ": the restored ledger does not reproduce the recorded root");
  pv::require(v8::conservation_failures(restored).empty(),
              name + ": a restored state must be conserved");

  // `assigned_permissions` is re-derived from the assignment records rather than
  // read, and the channel identity is stated over exactly this figure.
  pv::require(restored.assigned_permissions == ledger.assigned_permissions,
              name + ": the re-derived permission count differs");

  auto again = ps::encode_snapshot_v8(restored);
  pv::require(std::holds_alternative<ps::EncodedSnapshotV8>(again),
              name + ": a restored ledger must re-encode");
  pv::require(std::get<ps::EncodedSnapshotV8>(again).payload == raw,
              name + ": a restore and a re-encode are not the identity");

  // **This is a regression guard on a shape rather than a rule with a violating
  // input**, and it is worth saying which. Today it follows from the projection
  // comparison below, because the uptime entries are the only kinds 18 and 19 a
  // projection emits and it emits them raw. What it guards against is the change
  // that would break that: a restore that decoded these entries into a typed
  // shadow and re-encoded them on the way out would keep every root and every
  // projection intact while holding a second opinion about the key space the two
  // version-eight transitions write. That is the failure ADR 0026, ADR 0029, and
  // ADR 0046 each record, and this line is where it would be caught.
  pv::require(restored.uptime == ledger.uptime,
              name + ": the restored uptime map is not the one snapshotted");

  check_projection_is_lossless(restored, payload, name);
  check_still_executes(ledger, restored, name);
  return Counted{ledger.assigned_permissions, ledger.uptime.size()};
}

}  // namespace

void verify_round_trips(const pv::Values& values) {
  const std::array<std::pair<fixture::Scenario (*)(fixture::Signatures&),
                             const char*>,
                   4>
      scenarios{{
          {fixture::measured_scenario, "measured"},
          {fixture::disputed_scenario, "disputed"},
          {fixture::deadline_scenario, "deadline"},
          {fixture::carried_scenario, "carried"},
      }};
  std::size_t with_permissions = 0;
  std::size_t with_uptime = 0;
  for (const auto& [build, name] : scenarios) {
    const auto counted = check_scenario(values, build, name);
    if (counted.assigned_permissions != 0) ++with_permissions;
    if (counted.uptime_entries != 0) ++with_uptime;
  }
  // A re-derivation checked only against states that assigned nothing would hold
  // forever and establish nothing.
  pv::require(with_permissions >= 2,
              "at least two scenarios must have assigned a permission");
  // The same argument for the two entry kinds this version exists to carry: a
  // round trip over states that hold none of them would establish nothing about
  // them. `deadline` retains one of each and `measured` a window record.
  pv::require(with_uptime >= 2,
              "at least two scenarios must have retained an uptime entry");
}

}  // namespace snapshot_v8_tests

// The version-nine snapshot against the two recorded execution scenarios.
//
// **The evidence is a third source rather than a second opinion of the
// encoder.** Version eight's round trip compares the snapshot's root against a
// recorded `final_state_root`; version nine's execution vectors record no such
// figure, and the substitute is better aimed at what this slice adds. Each
// scenario's *restored* ledger is required to reproduce the recorded pool
// quantities and claim totals from
// `test-vectors/economy-transition-v9-execution.txt` — figures a Python model
// produced that knows nothing about snapshots, and figures that live in exactly
// the four new entry kinds and the widened kind-12 value this slice had to
// learn to write.
//
// A root would have proved "identical". These prove "the right things came
// back", which is the question a new entry kind actually raises.

#include "snapshot_v9_fixture.hpp"

#include <algorithm>
#include <array>
#include <span>
#include <utility>
#include <variant>

namespace snapshot_v9_tests {
namespace {

v9::Bytes encoded_of(const v9::Ledger& ledger, const std::string& name,
                     v9::Hash& root) {
  auto encoded = ps::encode_snapshot_v9(ledger);
  pv::require(std::holds_alternative<ps::EncodedSnapshotV9>(encoded),
              name + ": the final ledger must encode");
  auto value = std::get<ps::EncodedSnapshotV9>(std::move(encoded));
  root = value.state_root;
  return std::move(value.payload);
}

// One empty block advances the height and commits the empty transaction root, so
// running one on the original and on the restored ledger asks the only question
// a matching root cannot answer: whether what came back still executes.
//
// **The block needs a timestamp and the one it gets is the head's own**, which
// C2 admits because the rule is non-decreasing rather than strictly increasing.
// Reusing the head's stamp is deliberate: it is the value a restored ledger must
// have carried in order to produce a block at all, so a restore that dropped it
// would be executing against zero here and would diverge from the original at
// the first root rather than at some later boundary.
void check_still_executes(const v9::Ledger& original, const v9::Ledger& restored,
                          const std::string& name) {
  auto left = original;
  auto right = restored;
  const auto verify = v9::ed25519_verifier();
  const auto first = v9::execute_block(left, original.timestamp, {}, verify);
  const auto second = v9::execute_block(right, restored.timestamp, {}, verify);
  pv::require(first.has_value() && second.has_value(),
              name + ": a restored ledger must execute the next block");
  pv::require(first->block_id == second->block_id,
              name + ": the next block differs after a restore");
  pv::require(first->resulting_state_root == second->resulting_state_root,
              name + ": the next state root differs after a restore");
}

// The property that keeps the payload-root gate quiet: the rebuild is lossless,
// so the payload's entry list and the restored ledger's own projection are the
// same bytes.
void check_projection_is_lossless(const v9::Ledger& restored,
                                  const Payload& payload,
                                  const std::string& name) {
  auto projected = v9::economy_entries(restored);
  std::sort(projected.begin(), projected.end(),
            [](const v9::EconomyEntry& left, const v9::EconomyEntry& right) {
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

// **The timestamp is the field this version could lose in silence**, so it gets
// an aimed test rather than the coverage the gates happen to give it.
//
// A restore that dropped the stamp would hand back a ledger whose next block
// commits a root naming a height the stamp does not belong to — and every later
// block would still satisfy C2, because the stale stamp is smaller than anything
// that follows. The failure is a wrong root rather than a refusal.
//
// Two claims, and the second is the one that matters. The restored stamp equals
// the original. And a payload that keeps every other field and zeroes only the
// stamp reaches a **different** root, which is what proves the root commits to
// it rather than merely carrying it. Without the second claim the first could
// hold while the field was decorative.
void check_timestamp_survives(const v9::Ledger& original,
                              const v9::Ledger& restored,
                              const std::string& name) {
  pv::require(restored.timestamp == original.timestamp,
              name + ": a restored ledger lost the head's timestamp");
  pv::require(original.timestamp != 0,
              name + ": the scenario must reach a nonzero timestamp for this "
                     "check to establish anything");

  auto payload = payload_of(original);
  const auto committed = payload.state_root;
  payload.timestamp = 0;
  reseal(payload);
  pv::require(payload.state_root != committed,
              name + ": the state root does not commit to the timestamp");
}

// A payload whose stamp is zeroed but whose root still claims the original is
// what a restore actually meets if the field is dropped in transit. It must fail
// at gate 1, not be quietly accepted.
void check_a_dropped_timestamp_is_refused(const v9::Ledger& original,
                                          const ps::SnapshotParametersV9& parameters,
                                          const std::string& name) {
  auto payload = payload_of(original);
  payload.timestamp = 0;
  require_refusal(payload, parameters, ps::SnapshotV9Error::state_root_mismatch,
                  name + ": a payload whose timestamp was dropped");
}

// What a scenario contributed, so `verify_round_trips` can require that the
// evidence actually covers the surfaces the checks are about.
struct Counted {
  std::size_t claims = 0;
  std::size_t figures = 0;
  std::size_t window_months = 0;
  std::uint64_t assigned_permissions = 0;
  std::size_t uptime_entries = 0;
};

// The recorded figures, read out of the restored ledger rather than out of the
// ledger that was snapshotted. Reading them from the original would only prove
// the trace agrees with the vectors, which its own suite already establishes.
void check_recorded_quantities(const pv::Values& values,
                               const v9::Ledger& restored,
                               const std::string& name) {
  const auto expect = [&](const std::string& key, std::uint64_t actual) {
    const auto recorded = values.find(name + "." + key);
    pv::require(recorded != values.end(),
                "the vectors record no " + name + "." + key);
    pv::require(std::to_string(actual) == recorded->second,
                name + "." + key + ": a restored ledger holds " +
                    std::to_string(actual) + ", the vectors record " +
                    recorded->second);
  };
  expect("pool_accrued", restored.pool_accrued);
  expect("pool_payable", restored.pool_payable);
  expect("pool_minted", restored.pool_minted);

  std::uint64_t assigned = 0;
  std::uint64_t minted = 0;
  for (const auto& [seat, claim] : restored.claims) {
    (void)seat;
    assigned += claim.accrued_atomic;
    minted += claim.minted_atomic;
  }
  expect("claims_assigned", assigned);
  expect("claims_minted", minted);
}

Counted check_scenario(const pv::Values& values,
                       fixture::Scenario (*build)(fixture::Signatures&),
                       const std::string& name) {
  fixture::Signatures signatures;
  const auto scenario = build(signatures);
  const auto& ledger = scenario.ledger;

  v9::Hash root{};
  const auto raw = encoded_of(ledger, name, root);

  // The builder the refusals are constructed with, checked against the module
  // before any test uses it to build a refusal.
  const auto payload = payload_of(ledger);
  pv::require(payload.encode() == raw,
              name + ": the test's payload builder and the encoder disagree");

  const auto parameters = ps::snapshot_parameters(ledger);
  auto decoded = ps::decode_snapshot_v9(raw, parameters);
  pv::require(std::holds_alternative<ps::DecodedSnapshotV9>(decoded),
              name + ": a valid snapshot must restore");
  // Bound by value rather than by reference into the variant: the hosted matrix
  // runs a GCC whose `-Wdangling-reference` does not exist on this machine, and
  // a reference into a `std::get` result is exactly what it objects to.
  const v9::Ledger restored =
      std::get<ps::DecodedSnapshotV9>(std::move(decoded)).ledger;

  const auto restored_root = v9::ledger_state_root(restored);
  pv::require(restored_root.has_value(),
              name + ": a restored ledger commits a root");
  pv::require(*restored_root == root,
              name + ": the restored ledger does not reproduce the root it was "
                     "snapshotted at");
  pv::require(v9::conservation_failures(restored).empty(),
              name + ": a restored state must be conserved");

  check_recorded_quantities(values, restored, name);
  check_timestamp_survives(ledger, restored, name);
  check_a_dropped_timestamp_is_refused(ledger, parameters, name);

  // `assigned_permissions` is re-derived from the assignment records rather than
  // read, and the channel identity is stated over exactly this figure.
  pv::require(restored.assigned_permissions == ledger.assigned_permissions,
              name + ": the re-derived permission count differs");

  // The four typed maps version nine adds, compared whole. A projection that
  // round-tripped the entries while rebuilding a different map would pass every
  // root check and fail here.
  pv::require(restored.window_months == ledger.window_months,
              name + ": the restored window months differ");
  pv::require(restored.figures == ledger.figures,
              name + ": the restored monthly figures differ");
  pv::require(restored.claims == ledger.claims,
              name + ": the restored monthly claims differ");
  pv::require(restored.accumulating_month == ledger.accumulating_month,
              name + ": the restored settlement cursor differs");

  auto again = ps::encode_snapshot_v9(restored);
  pv::require(std::holds_alternative<ps::EncodedSnapshotV9>(again),
              name + ": a restored ledger must re-encode");
  pv::require(std::get<ps::EncodedSnapshotV9>(again).payload == raw,
              name + ": a restore and a re-encode are not the identity");

  // A regression guard on a shape rather than a rule with a violating input.
  // A restore that decoded the uptime entries into a typed shadow and re-encoded
  // them on the way out would keep every root and every projection intact while
  // holding a second opinion about the key space the two version-eight
  // transitions write.
  pv::require(restored.uptime == ledger.uptime,
              name + ": the restored uptime map is not the one snapshotted");

  check_projection_is_lossless(restored, payload, name);
  check_still_executes(ledger, restored, name);
  return Counted{ledger.claims.size(), ledger.figures.size(),
                 ledger.window_months.size(), ledger.assigned_permissions,
                 ledger.uptime.size()};
}

}  // namespace

void verify_round_trips(const pv::Values& values) {
  const std::array<std::pair<fixture::Scenario (*)(fixture::Signatures&),
                             const char*>,
                   2>
      scenarios{{
          {fixture::settled_scenario, "settled"},
          {fixture::halted_scenario, "halted"},
      }};
  Counted total;
  std::size_t with_claims = 0;
  for (const auto& [build, name] : scenarios) {
    const auto counted = check_scenario(values, build, name);
    if (counted.claims != 0) ++with_claims;
    total.claims += counted.claims;
    total.figures += counted.figures;
    total.window_months += counted.window_months;
    total.assigned_permissions += counted.assigned_permissions;
    total.uptime_entries += counted.uptime_entries;
  }
  // A round trip over states holding none of the four new kinds would establish
  // nothing about them, so the coverage is required rather than hoped for.
  pv::require(with_claims == scenarios.size(),
              "every scenario must have paid a claim for the round trip to "
              "exercise kind 22");
  pv::require(total.figures != 0,
              "the scenarios must retain a monthly figure, or kind 21 is "
              "untested");
  pv::require(total.window_months != 0,
              "the scenarios must retain a window month, or kind 20 is "
              "untested");
  pv::require(total.assigned_permissions != 0,
              "the scenarios must have assigned a permission, or the "
              "re-derivation establishes nothing");
  pv::require(total.uptime_entries != 0,
              "the scenarios must retain an uptime entry, or the two kinds "
              "version eight added are untested here");
}

}  // namespace snapshot_v9_tests

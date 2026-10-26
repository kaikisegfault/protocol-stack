// The version-ten snapshot against the three recorded execution fixtures.
//
// **The evidence is a third source rather than a second opinion of the
// encoder.** Each fixture's *restored* ledger is required to commit the final
// root `test-vectors/economy-transition-v10-execution.txt` records for it, and
// the population's to hold the retirement height the vectors record. A Python
// model produced those figures, and it knows nothing about snapshots.
//
// The three fixtures between them hold every entry kind version ten adds. The
// chain holds two machine keys, their owners, and a founder count. The
// population holds 101 machine keys and owners, both founders' counts, and the
// launch key's retirement. The span run holds 732 assignment records behind
// one machine.
//
// A root proves "identical". The rest of this file proves "the right things
// came back": the four registry maps compared whole, and the one field no root
// commits to, the build authority key, aimed at with the one transaction that
// reads it.

#include "snapshot_v10_fixture.hpp"

#include <algorithm>
#include <set>
#include <utility>
#include <variant>
#include <vector>

namespace snapshot_v10_tests {
namespace {

using fixture::Person;

// One fixture the round trip restores, and the founder and seat whose machine
// key the build-authority probe replaces.
struct Subject {
  std::string name;
  std::string root_key;
  const v10::Ledger* ledger = nullptr;
  fixture::Signatures* signatures = nullptr;
  Person founder;
  std::uint32_t seat_id = 0;
};

v10::Bytes encoded_of(const v10::Ledger& ledger, const std::string& name) {
  auto encoded = ps::encode_snapshot_v10(ledger);
  pv::require(std::holds_alternative<ps::EncodedSnapshotV10>(encoded),
              name + ": the final ledger must encode");
  return std::get<ps::EncodedSnapshotV10>(std::move(encoded)).payload;
}

// One empty block at the head's own stamp, which C2 admits because the rule is
// non-decreasing. It asks the only question a matching root cannot answer:
// whether what came back still executes.
void check_still_executes(const v10::Ledger& original, const v10::Ledger& restored,
                          const std::string& name) {
  auto left = original;
  auto right = restored;
  const auto verify = v10::ed25519_verifier();
  const auto first = v10::execute_block(left, original.timestamp, {}, verify);
  const auto second = v10::execute_block(right, restored.timestamp, {}, verify);
  pv::require(first.has_value() && second.has_value(),
              name + ": a restored ledger must execute the next block");
  pv::require(first->block_id == second->block_id,
              name + ": the next block differs after a restore");
}

// The property that keeps the payload-root gate quiet: the rebuild is lossless,
// so the payload's entry list and the restored ledger's own projection are the
// same bytes.
void check_projection_is_lossless(const v10::Ledger& restored,
                                  const Payload& payload, const std::string& name) {
  auto projected = v10::economy_entries(restored);
  std::sort(projected.begin(), projected.end(),
            [](const v10::EconomyEntry& left, const v10::EconomyEntry& right) {
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

// Version nine's aimed check, carried: the root commits to the stamp, so a
// payload that keeps everything else and zeroes it reaches another root, and a
// payload that drops it in transit stops at gate 1 (ADR 0080).
void check_timestamp(const v10::Ledger& original, const v10::Ledger& restored,
                     const std::string& name) {
  pv::require(original.timestamp != 0 && restored.timestamp == original.timestamp,
              name + ": a restored ledger lost the head's timestamp");
  auto payload = payload_of(original);
  const auto committed = payload.state_root;
  payload.timestamp = 0;
  require_refusal(payload, ps::snapshot_parameters(original),
                  ps::SnapshotV10Error::state_root_mismatch,
                  name + ": a payload whose timestamp was dropped");
  reseal(payload);
  pv::require(payload.state_root != committed,
              name + ": the state root does not commit to the timestamp");
}

// One block holding one kind-23 replacement of the subject's machine key,
// executed on a copy of `ledger`. Its attestation is signed by the build
// authority key the fixture's genesis carries.
v10::BlockOutcome replace_machine_key(const Subject& subject,
                                      const v10::Ledger& ledger) {
  auto copy = ledger;
  const fixture::Builder build(*subject.signatures, copy);
  const auto height = copy.height + 1;
  const auto raw = build.machine_registration(
      subject.founder, subject.seat_id, fixture::machine_key(subject.seat_id, 9),
      fixture::nonce_of(copy, subject.founder.escrow()) + 1,
      height + fixture::kLifetime);
  const std::vector<v10::Bytes> inputs{raw};
  auto block = v10::execute_block(copy, fixture::timestamp_of_height(height),
                                  inputs, subject.signatures->verifier());
  pv::require(block.has_value() && block->executed.size() == 1,
              subject.name + ": the kind-23 block executes");
  return std::move(*block);
}

// **The build authority key is the field version ten could lose in silence**
// (ADR 0108). No root commits to it, so a restore that dropped it would pass
// all three gates and then refuse every machine key the network admits.
//
// Three claims. The root is the same with the key zeroed, which is why the
// gates cannot catch it and the parameter comparison must. The restored ledger
// accepts a kind-23 replacement exactly as the original does. And the same
// block on a ledger that lost the key is refused as `UNAUTHORIZED`, which is
// what proves the probe reads the field rather than passing around it.
void check_build_authority(const Subject& subject, const v10::Ledger& restored) {
  const auto& original = *subject.ledger;
  pv::require(restored.build_authority_key == original.build_authority_key,
              subject.name + ": a restored ledger lost the build authority key");

  auto lost = restored;
  lost.build_authority_key = v10::Octets32{};
  pv::require(v10::ledger_state_root(lost) == v10::ledger_state_root(restored),
              subject.name + ": the root is expected not to commit to the build "
                             "authority key");

  const auto expected = replace_machine_key(subject, original);
  const auto actual = replace_machine_key(subject, restored);
  pv::require(expected.executed.front().outcome.succeeded(),
              subject.name + ": the probe's replacement must succeed");
  pv::require(actual.block_id == expected.block_id &&
                  actual.resulting_state_root == expected.resulting_state_root,
              subject.name + ": a restored ledger executes kind 23 differently");

  const auto refused = replace_machine_key(subject, lost);
  pv::require(refused.executed.front().outcome.result == v10::Result::unauthorized,
              subject.name + ": a ledger without the build authority key must "
                             "refuse the attestation");
}

// The four registry maps compared whole, beside version nine's four. A
// projection that round-tripped the entries while rebuilding a different map
// would pass every root check and fail here.
void check_maps(const v10::Ledger& original, const v10::Ledger& restored,
                const std::string& name) {
  pv::require(restored.machine_keys == original.machine_keys,
              name + ": the restored machine keys differ");
  pv::require(restored.machine_key_owners == original.machine_key_owners,
              name + ": the restored machine-key owners differ");
  pv::require(restored.launch_retired_at == original.launch_retired_at,
              name + ": the restored retirement differs");
  pv::require(restored.founder_registrations == original.founder_registrations,
              name + ": the restored founder counts differ");
  pv::require(restored.window_months == original.window_months &&
                  restored.figures == original.figures &&
                  restored.claims == original.claims &&
                  restored.accumulating_month == original.accumulating_month,
              name + ": the restored monthly settlement differs");
  // Version eight's raw uptime map, kept raw: a restore that decoded it into a
  // typed shadow would hold a second opinion of the key space it carries.
  pv::require(restored.uptime == original.uptime,
              name + ": the restored uptime map is not the one snapshotted");
  pv::require(restored.assigned_permissions == original.assigned_permissions,
              name + ": the re-derived permission count differs");
}

v10::Ledger restore(const Subject& subject, const pv::Values& values) {
  const auto& ledger = *subject.ledger;
  const auto raw = encoded_of(ledger, subject.name);
  // The builder the refusals are made with, checked against the module before
  // any test uses it to build one.
  pv::require(payload_of(ledger).encode() == raw,
              subject.name + ": the test's payload builder and the encoder disagree");
  auto decoded = ps::decode_snapshot_v10(raw, ps::snapshot_parameters(ledger));
  pv::require(std::holds_alternative<ps::DecodedSnapshotV10>(decoded),
              subject.name + ": a valid snapshot must restore");
  // By value rather than by reference into the variant, which is the shape
  // GCC 13's `-Wdangling-reference` objects to.
  const v10::Ledger restored =
      std::get<ps::DecodedSnapshotV10>(std::move(decoded)).ledger;

  const auto root = v10::ledger_state_root(restored);
  pv::require(root.has_value(), subject.name + ": a restored ledger commits a root");
  const auto recorded = values.find(subject.root_key);
  pv::require(recorded != values.end(), "the vectors record no " + subject.root_key);
  pv::require(fixture::hex(*root) == recorded->second,
              subject.name + ": the restored root is not the one the vectors record");
  pv::require(v10::conservation_failures(restored).empty(),
              subject.name + ": a restored state must be conserved");

  auto again = ps::encode_snapshot_v10(restored);
  pv::require(std::holds_alternative<ps::EncodedSnapshotV10>(again) &&
                  std::get<ps::EncodedSnapshotV10>(again).payload == raw,
              subject.name + ": a restore and a re-encode are not the identity");
  return restored;
}

}  // namespace

void verify_round_trips(const pv::Values& values, Fixtures& fixtures) {
  const std::vector<Subject> subjects{
      {"chain", "chain.final_root", &fixtures.chain.ledger,
       &fixtures.chain_signatures, fixture::kAlice, 0},
      {"cutoff", "cap.final_root", &fixtures.cutoff.ledger,
       &fixtures.cutoff.signatures, fixture::kPopulationFounder, 0},
      {"span", "span.final_root", &fixtures.span.ledger, &fixtures.span.signatures,
       fixture::kPopulationFounder, 0},
  };
  std::set<std::uint8_t> kinds;
  for (const auto& subject : subjects) {
    const auto restored = restore(subject, values);
    check_maps(*subject.ledger, restored, subject.name);
    check_timestamp(*subject.ledger, restored, subject.name);
    check_build_authority(subject, restored);
    check_projection_is_lossless(restored, payload_of(*subject.ledger),
                                 subject.name);
    check_still_executes(*subject.ledger, restored, subject.name);
    for (const auto& entry : v10::economy_entries(restored)) {
      kinds.insert(entry.key.front());
    }
  }

  // The retirement is the one registry value the vectors fix, so it is read out
  // of a restored ledger rather than out of the one that was snapshotted.
  const auto retired = ps::decode_snapshot_v10(
      encoded_of(fixtures.cutoff.ledger, "cutoff"),
      ps::snapshot_parameters(fixtures.cutoff.ledger));
  pv::require(std::holds_alternative<ps::DecodedSnapshotV10>(retired),
              "the population restores");
  const auto at = std::get<ps::DecodedSnapshotV10>(retired).ledger.launch_retired_at;
  fixture::agree(values, "cutoff.registry.retired_at_height", at.value_or(0));

  // A round trip over states holding none of the kinds this version adds would
  // establish nothing about them, so the coverage is required.
  for (const auto kind :
       {v10::Entry::machine_key, v10::Entry::launch_retirement,
        v10::Entry::machine_key_owner, v10::Entry::founder_registrations,
        v10::Entry::monthly_pool_claim, v10::Entry::monthly_uptime_figure,
        v10::Entry::seat_window, v10::Entry::referral_balance,
        v10::Entry::typed_custody}) {
    pv::require(kinds.contains(static_cast<std::uint8_t>(kind)),
                "no round-trip fixture holds an entry of kind " +
                    std::to_string(static_cast<unsigned>(kind)));
  }
}

}  // namespace snapshot_v10_tests

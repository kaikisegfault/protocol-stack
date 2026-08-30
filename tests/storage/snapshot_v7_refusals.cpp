// The framing refusals and the three restore gates.
//
// **Every negative case here is a payload with a valid digest**, built by the
// fixture's own encoder rather than by flipping a byte, except the two cases
// whose subject *is* a flipped byte. A decoder tested only against corrupted
// bytes is tested only against its digest.
//
// The conservation gate is the one that matters most and it is the reason the
// restore re-derives `assigned_permissions` instead of reading it: an adversary
// who edits a state and reseals it defeats both root gates by construction, and
// only an identity that must still hold refuses them.

#include "snapshot_v7_fixture.hpp"

#include <variant>

namespace snapshot_v7_tests {
namespace {

Payload pool_payload(ps::SnapshotParametersV7& parameters) {
  fixture::Signatures signatures;
  const auto scenario = fixture::pool_scenario(signatures);
  parameters = ps::snapshot_parameters(scenario.ledger);
  return payload_of(scenario.ledger);
}

void require_raw_refusal(const v7::Bytes& raw,
                         const ps::SnapshotParametersV7& parameters,
                         ps::SnapshotV7Error expected,
                         const std::string& subject) {
  const auto decoded = ps::decode_snapshot_v7(raw, parameters);
  pv::require(std::holds_alternative<ps::SnapshotV7Error>(decoded),
              subject + ": a restore accepted it");
  const auto actual = std::get<ps::SnapshotV7Error>(decoded);
  pv::require(actual == expected, subject + ": expected " + error_name(expected) +
                                      ", got " + error_name(actual));
}

void check_shape(const Payload& base, const ps::SnapshotParametersV7& parameters) {
  const auto raw = base.encode();
  for (std::size_t length = 0; length < 190; length += 47) {
    require_raw_refusal(v7::Bytes(raw.begin(), raw.begin() + length), parameters,
                        ps::SnapshotV7Error::malformed, "a payload below the fixed size");
  }
  auto wrong_magic = base;
  wrong_magic.magic = {'P', 'S', 'S', '7'};
  require_refusal(wrong_magic, parameters, ps::SnapshotV7Error::malformed,
                  "a payload under another magic");
  // Version one's own magic with version one's number: recognised as the family
  // and refused as the wrong member of it, which is what the version field buys.
  auto wrong_version = base;
  wrong_version.version = 1;
  require_refusal(wrong_version, parameters, ps::SnapshotV7Error::unsupported_version,
                  "a version-one snapshot");

  auto corrupted = raw;
  corrupted[raw.size() / 2] ^= 0x01;
  require_raw_refusal(corrupted, parameters, ps::SnapshotV7Error::digest_mismatch,
                      "a payload with one flipped octet");
  auto corrupted_digest = raw;
  corrupted_digest.back() ^= 0x80;
  require_raw_refusal(corrupted_digest, parameters, ps::SnapshotV7Error::digest_mismatch,
                      "a payload with a rewritten digest");
}

void check_parameters(const Payload& base,
                      const ps::SnapshotParametersV7& parameters) {
  auto other_chain = parameters;
  other_chain.chain_id[0] ^= 0xFF;
  require_refusal(base, other_chain, ps::SnapshotV7Error::immutable_parameters_mismatch,
                  "a restore onto another chain");
  auto other_limit = parameters;
  other_limit.supply_limit += 1;
  require_refusal(base, other_limit, ps::SnapshotV7Error::immutable_parameters_mismatch,
                  "a restore under another supply limit");
  auto other_fee = parameters;
  other_fee.fixed_fee += 1;
  require_refusal(base, other_fee, ps::SnapshotV7Error::immutable_parameters_mismatch,
                  "a restore under another fee");
  auto other_key = parameters;
  other_key.verifier_key[31] ^= 0xFF;
  require_refusal(base, other_key, ps::SnapshotV7Error::immutable_parameters_mismatch,
                  "a restore under another verifier key");
}

void check_sections(const Payload& base, const ps::SnapshotParametersV7& parameters) {
  auto over_declared = base;
  over_declared.declared_account_count = base.accounts.size() + 1;
  require_refusal(over_declared, parameters, ps::SnapshotV7Error::malformed,
                  "a payload claiming an account it does not carry");
  auto under_declared = base;
  under_declared.declared_economy_count = base.economy.size() - 1;
  require_refusal(under_declared, parameters, ps::SnapshotV7Error::malformed,
                  "a payload with an entry nothing reads");
  auto huge = base;
  huge.declared_economy_count = ~std::uint64_t{0};
  require_refusal(huge, parameters, ps::SnapshotV7Error::size_overflow,
                  "a payload claiming more entries than octets");

  auto unordered_accounts = base;
  pv::require(unordered_accounts.accounts.size() >= 2,
              "the fixture carries at least two accounts");
  std::swap(unordered_accounts.accounts[0], unordered_accounts.accounts[1]);
  require_refusal(unordered_accounts, parameters, ps::SnapshotV7Error::malformed,
                  "an account map out of order");
  auto repeated_account = base;
  repeated_account.accounts[1] = repeated_account.accounts[0];
  require_refusal(repeated_account, parameters, ps::SnapshotV7Error::malformed,
                  "an account map with a repeated identifier");

  auto unordered_entries = base;
  std::swap(unordered_entries.economy[0], unordered_entries.economy[1]);
  require_refusal(unordered_entries, parameters, ps::SnapshotV7Error::malformed,
                  "an economy map out of order");
  auto repeated_entry = base;
  repeated_entry.economy[1] = repeated_entry.economy[0];
  require_refusal(repeated_entry, parameters, ps::SnapshotV7Error::malformed,
                  "an economy map with a repeated key");
}

void check_gates(const Payload& base, const ps::SnapshotParametersV7& parameters) {
  // Gate 1. The summary is inside the root, so a payload that edits one field
  // and keeps its root no longer projects to what it claims.
  auto moved_height = base;
  moved_height.height += 1;
  require_refusal(moved_height, parameters, ps::SnapshotV7Error::state_root_mismatch,
                  "a payload at a height its root does not commit to");
  auto other_root = base;
  other_root.state_root[0] ^= 0xFF;
  require_refusal(other_root, parameters, ps::SnapshotV7Error::state_root_mismatch,
                  "a payload claiming a root nothing in it produces");

  // Gate 3, and the case the whole re-derivation exists for. Both root gates are
  // defeated by resealing, so an edited state arrives at the conservation check
  // with nothing left to catch it but an identity that must still hold.
  auto inflated = base;
  auto& channel = entry_of(inflated, v7::Entry::channel);
  poke_u64(channel.value, 0, ~std::uint64_t{0} / 2);
  reseal(inflated);
  require_refusal(inflated, parameters, ps::SnapshotV7Error::not_conserved,
                  "a resealed payload that issued value from nowhere");

  // Deleting an assignment record lowers the re-derived permission count while
  // `outstanding` still holds what that cycle assigned. A snapshot that carried
  // the count could have lowered it to match; one that re-derives it cannot.
  auto without_record = base;
  const auto record = find_entry(without_record, v7::Entry::cycle_assignment);
  pv::require(record != without_record.economy.end(),
              "the pool scenario records a cycle assignment");
  without_record.economy.erase(record);
  reseal(without_record);
  require_refusal(without_record, parameters, ps::SnapshotV7Error::not_conserved,
                  "a resealed payload with an assignment record removed");
}

}  // namespace

void verify_framing_refusals() {
  ps::SnapshotParametersV7 parameters;
  const auto base = pool_payload(parameters);
  // The base itself must restore, or every refusal below is vacuous.
  const auto decoded = ps::decode_snapshot_v7(base.encode(), parameters);
  pv::require(std::holds_alternative<ps::DecodedSnapshotV7>(decoded),
              "the refusal fixture's own payload must restore");

  check_shape(base, parameters);
  check_parameters(base, parameters);
  check_sections(base, parameters);
  check_gates(base, parameters);
}

}  // namespace snapshot_v7_tests

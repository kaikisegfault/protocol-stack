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

#include "snapshot_v8_fixture.hpp"

#include <variant>

namespace snapshot_v8_tests {
namespace {

// `measured` is the base for the same reason `pool` was version seven's: it is
// the scenario that carries the widest set of entry kinds, including the one
// cycle assignment record and the one seat window record the gates below reach
// for.
Payload measured_payload(ps::SnapshotParametersV8& parameters) {
  fixture::Signatures signatures;
  const auto scenario = fixture::measured_scenario(signatures);
  parameters = ps::snapshot_parameters(scenario.ledger);
  return payload_of(scenario.ledger);
}

// The one scenario that retains an open challenge, which no other does.
Payload deadline_payload(ps::SnapshotParametersV8& parameters) {
  fixture::Signatures signatures;
  const auto scenario = fixture::deadline_scenario(signatures);
  parameters = ps::snapshot_parameters(scenario.ledger);
  return payload_of(scenario.ledger);
}

void require_raw_refusal(const v8::Bytes& raw,
                         const ps::SnapshotParametersV8& parameters,
                         ps::SnapshotV8Error expected,
                         const std::string& subject) {
  const auto decoded = ps::decode_snapshot_v8(raw, parameters);
  pv::require(std::holds_alternative<ps::SnapshotV8Error>(decoded),
              subject + ": a restore accepted it");
  const auto actual = std::get<ps::SnapshotV8Error>(decoded);
  pv::require(actual == expected, subject + ": expected " + error_name(expected) +
                                      ", got " + error_name(actual));
}

void check_shape(const Payload& base, const ps::SnapshotParametersV8& parameters) {
  const auto raw = base.encode();
  // Version eight's `kFixedSize`: the 158-octet prefix plus a root and a digest.
  for (std::size_t length = 0; length < 222; length += 53) {
    require_raw_refusal(v8::Bytes(raw.begin(), raw.begin() + length), parameters,
                        ps::SnapshotV8Error::malformed, "a payload below the fixed size");
  }
  auto wrong_magic = base;
  wrong_magic.magic = {'P', 'S', 'S', '7'};
  require_refusal(wrong_magic, parameters, ps::SnapshotV8Error::malformed,
                  "a payload under another magic");
  // Version one's own magic with version one's number: recognised as the family
  // and refused as the wrong member of it, which is what the version field buys.
  auto wrong_version = base;
  wrong_version.version = 1;
  require_refusal(wrong_version, parameters, ps::SnapshotV8Error::unsupported_version,
                  "a version-one snapshot");
  // And version seven's, which is the member of the family this one replaces.
  // Its prefix is thirty-two octets shorter, so without the version field a
  // reader would find every field after the verifier key at the wrong offset.
  auto predecessor = base;
  predecessor.version = 7;
  require_refusal(predecessor, parameters, ps::SnapshotV8Error::unsupported_version,
                  "a version-seven snapshot");

  auto corrupted = raw;
  corrupted[raw.size() / 2] ^= 0x01;
  require_raw_refusal(corrupted, parameters, ps::SnapshotV8Error::digest_mismatch,
                      "a payload with one flipped octet");
  auto corrupted_digest = raw;
  corrupted_digest.back() ^= 0x80;
  require_raw_refusal(corrupted_digest, parameters, ps::SnapshotV8Error::digest_mismatch,
                      "a payload with a rewritten digest");
}

void check_parameters(const Payload& base,
                      const ps::SnapshotParametersV8& parameters) {
  auto other_chain = parameters;
  other_chain.chain_id[0] ^= 0xFF;
  require_refusal(base, other_chain, ps::SnapshotV8Error::immutable_parameters_mismatch,
                  "a restore onto another chain");
  auto other_limit = parameters;
  other_limit.supply_limit += 1;
  require_refusal(base, other_limit, ps::SnapshotV8Error::immutable_parameters_mismatch,
                  "a restore under another supply limit");
  auto other_fee = parameters;
  other_fee.fixed_fee += 1;
  require_refusal(base, other_fee, ps::SnapshotV8Error::immutable_parameters_mismatch,
                  "a restore under another fee");
  auto other_key = parameters;
  other_key.verifier_key[31] ^= 0xFF;
  require_refusal(base, other_key, ps::SnapshotV8Error::immutable_parameters_mismatch,
                  "a restore under another verifier key");
  // Version eight's fifth parameter, and the only one with no second copy in the
  // payload: nothing in the state root commits to it, so this comparison is the
  // whole of what stops a restored node answering to a different dispute
  // authority than its peers.
  auto other_authority = parameters;
  other_authority.dispute_authority_key[0] ^= 0xFF;
  require_refusal(base, other_authority,
                  ps::SnapshotV8Error::immutable_parameters_mismatch,
                  "a restore under another dispute authority key");
}

void check_sections(const Payload& base, const ps::SnapshotParametersV8& parameters) {
  auto over_declared = base;
  over_declared.declared_account_count = base.accounts.size() + 1;
  require_refusal(over_declared, parameters, ps::SnapshotV8Error::malformed,
                  "a payload claiming an account it does not carry");
  auto under_declared = base;
  under_declared.declared_economy_count = base.economy.size() - 1;
  require_refusal(under_declared, parameters, ps::SnapshotV8Error::malformed,
                  "a payload with an entry nothing reads");
  auto huge = base;
  huge.declared_economy_count = ~std::uint64_t{0};
  require_refusal(huge, parameters, ps::SnapshotV8Error::size_overflow,
                  "a payload claiming more entries than octets");

  auto unordered_accounts = base;
  pv::require(unordered_accounts.accounts.size() >= 2,
              "the fixture carries at least two accounts");
  std::swap(unordered_accounts.accounts[0], unordered_accounts.accounts[1]);
  require_refusal(unordered_accounts, parameters, ps::SnapshotV8Error::malformed,
                  "an account map out of order");
  auto repeated_account = base;
  repeated_account.accounts[1] = repeated_account.accounts[0];
  require_refusal(repeated_account, parameters, ps::SnapshotV8Error::malformed,
                  "an account map with a repeated identifier");

  auto unordered_entries = base;
  std::swap(unordered_entries.economy[0], unordered_entries.economy[1]);
  require_refusal(unordered_entries, parameters, ps::SnapshotV8Error::malformed,
                  "an economy map out of order");
  auto repeated_entry = base;
  repeated_entry.economy[1] = repeated_entry.economy[0];
  require_refusal(repeated_entry, parameters, ps::SnapshotV8Error::malformed,
                  "an economy map with a repeated key");
}

void check_gates(const Payload& base, const ps::SnapshotParametersV8& parameters) {
  // Gate 1. The summary is inside the root, so a payload that edits one field
  // and keeps its root no longer projects to what it claims.
  auto moved_height = base;
  moved_height.height += 1;
  require_refusal(moved_height, parameters, ps::SnapshotV8Error::state_root_mismatch,
                  "a payload at a height its root does not commit to");
  auto other_root = base;
  other_root.state_root[0] ^= 0xFF;
  require_refusal(other_root, parameters, ps::SnapshotV8Error::state_root_mismatch,
                  "a payload claiming a root nothing in it produces");

  // Gate 3, and the case the whole re-derivation exists for. Both root gates are
  // defeated by resealing, so an edited state arrives at the conservation check
  // with nothing left to catch it but an identity that must still hold.
  auto inflated = base;
  auto& channel = entry_of(inflated, v8::Entry::channel);
  poke_u64(channel.value, 0, ~std::uint64_t{0} / 2);
  reseal(inflated);
  require_refusal(inflated, parameters, ps::SnapshotV8Error::not_conserved,
                  "a resealed payload that issued value from nowhere");

  // Deleting an assignment record lowers the re-derived permission count while
  // `outstanding` still holds what that cycle assigned. A snapshot that carried
  // the count could have lowered it to match; one that re-derives it cannot.
  auto without_record = base;
  const auto record = find_entry(without_record, v8::Entry::cycle_assignment);
  pv::require(record != without_record.economy.end(),
              "the pool scenario records a cycle assignment");
  without_record.economy.erase(record);
  reseal(without_record);
  require_refusal(without_record, parameters, ps::SnapshotV8Error::not_conserved,
                  "a resealed payload with an assignment record removed");

  // Version eight's retention rule, reached through a resealed payload. The
  // entry decodes and the record is a state some block wrote — it is *where* it
  // is that no sequence of blocks could have left it, because the prologue
  // deletes a window's records two windows after it closes. Only the third gate
  // can say so.
  auto stale_window = base;
  auto& window = last_of(stale_window, v8::Entry::seat_window);
  poke_u64(window.key, 1, 0);
  reseal(stale_window);
  require_refusal(stale_window, parameters, ps::SnapshotV8Error::not_conserved,
                  "a resealed payload retaining a window past its retention");
}

// The other half of the same argument, on the scenario that has an open
// challenge to move. A challenge whose deadline has passed is a state the expiry
// step cannot leave behind, and again the entry itself is well formed.
void check_challenge_gate() {
  ps::SnapshotParametersV8 parameters;
  const auto base = deadline_payload(parameters);
  const auto decoded = ps::decode_snapshot_v8(base.encode(), parameters);
  pv::require(std::holds_alternative<ps::DecodedSnapshotV8>(decoded),
              "the deadline scenario's own payload must restore");

  auto expired = base;
  auto& challenge = last_of(expired, v8::Entry::open_challenge);
  poke_u64(challenge.key, 1, 0);
  reseal(expired);
  require_refusal(expired, parameters, ps::SnapshotV8Error::not_conserved,
                  "a resealed payload retaining an expired challenge");
}

}  // namespace

void verify_framing_refusals() {
  ps::SnapshotParametersV8 parameters;
  const auto base = measured_payload(parameters);
  // The base itself must restore, or every refusal below is vacuous.
  const auto decoded = ps::decode_snapshot_v8(base.encode(), parameters);
  pv::require(std::holds_alternative<ps::DecodedSnapshotV8>(decoded),
              "the refusal fixture's own payload must restore");

  check_shape(base, parameters);
  check_parameters(base, parameters);
  check_sections(base, parameters);
  check_gates(base, parameters);
  check_challenge_gate();
}

}  // namespace snapshot_v8_tests

// The framing a restore refuses: the prefix, the digest, the two ordered
// sections, the declared counts, and the three gates.
//
// Every case below mutates one field of a payload the module has already
// accepted, so a refusal names the field rather than the fixture. The last check
// in the file re-restores the unmutated payload, which is what keeps a passing
// suite from being a suite that refuses everything.

#include "snapshot_v9_fixture.hpp"

#include <string>
#include <variant>

namespace snapshot_v9_tests {
namespace {

// A payload that is structurally fine and lies about exactly one immutable
// parameter. All five reach the same gate, and each is named so a regression
// says which one stopped being compared.
void check_parameter_refusals(const Payload& original,
                              const ps::SnapshotParametersV9& parameters) {
  {
    auto payload = original;
    payload.chain_id[0] ^= 0xFFU;
    require_refusal(payload, parameters,
                    ps::SnapshotV9Error::immutable_parameters_mismatch,
                    "a restore onto another chain");
  }
  {
    auto payload = original;
    payload.supply_limit += 1;
    require_refusal(payload, parameters,
                    ps::SnapshotV9Error::immutable_parameters_mismatch,
                    "a restore under another supply limit");
  }
  {
    auto payload = original;
    payload.fixed_fee += 1;
    require_refusal(payload, parameters,
                    ps::SnapshotV9Error::immutable_parameters_mismatch,
                    "a restore under another fee");
  }
  {
    auto payload = original;
    payload.verifier_key[0] ^= 0xFFU;
    require_refusal(payload, parameters,
                    ps::SnapshotV9Error::immutable_parameters_mismatch,
                    "a restore under another verifier key");
  }
  {
    // The one parameter no state entry carries a second copy of, which is why it
    // is compared at all: nothing in the root commits to it, so a payload could
    // otherwise move a restored node to another dispute authority unnoticed.
    auto payload = original;
    payload.dispute_authority_key[0] ^= 0xFFU;
    require_refusal(payload, parameters,
                    ps::SnapshotV9Error::immutable_parameters_mismatch,
                    "a restore under another dispute authority key");
  }
}

void check_section_refusals(const Payload& original,
                            const ps::SnapshotParametersV9& parameters) {
  pv::require(original.accounts.size() >= 2,
              "the fixture carries at least two accounts");
  {
    auto payload = original;
    std::swap(payload.accounts[0], payload.accounts[1]);
    reseal(payload);
    require_refusal(payload, parameters, ps::SnapshotV9Error::malformed,
                    "an account map out of order");
  }
  {
    auto payload = original;
    payload.accounts[1] = payload.accounts[0];
    reseal(payload);
    require_refusal(payload, parameters, ps::SnapshotV9Error::malformed,
                    "an account map with a repeated identifier");
  }
  {
    auto payload = original;
    std::swap(payload.economy[0], payload.economy[1]);
    reseal(payload);
    require_refusal(payload, parameters, ps::SnapshotV9Error::malformed,
                    "an economy map out of order");
  }
  {
    auto payload = original;
    payload.economy[1] = payload.economy[0];
    reseal(payload);
    require_refusal(payload, parameters, ps::SnapshotV9Error::malformed,
                    "an economy map with a repeated key");
  }
  {
    // Every octet between the prefix and the root must belong to a section. A
    // payload with a tail nothing reads could carry two states under one digest.
    auto payload = original;
    payload.declared_economy_count =
        static_cast<std::uint64_t>(payload.economy.size()) - 1;
    require_refusal(payload, parameters, ps::SnapshotV9Error::malformed,
                    "a payload with an entry nothing reads");
  }
  {
    auto payload = original;
    payload.declared_account_count =
        static_cast<std::uint64_t>(payload.accounts.size()) + 1;
    require_refusal(payload, parameters, ps::SnapshotV9Error::malformed,
                    "a payload claiming an account it does not carry");
  }
  {
    // Bounded against the payload before it is used as a length, so an absurd
    // count is refused rather than reserved for.
    auto payload = original;
    payload.declared_economy_count = 1ULL << 40U;
    require_refusal(payload, parameters, ps::SnapshotV9Error::size_overflow,
                    "a payload claiming more entries than octets");
  }
}

void check_gate_refusals(const Payload& original,
                         const ps::SnapshotParametersV9& parameters) {
  {
    // Gate 1: the rebuilt ledger's own projection no longer produces the root
    // the payload claims.
    auto payload = original;
    payload.height += 1;
    require_refusal(payload, parameters,
                    ps::SnapshotV9Error::state_root_mismatch,
                    "a payload at a height its root does not commit to");
  }
  {
    auto payload = original;
    payload.state_root[0] ^= 0xFFU;
    require_refusal(payload, parameters,
                    ps::SnapshotV9Error::state_root_mismatch,
                    "a payload claiming a root nothing in it produces");
  }
  {
    // Gate 3, and the adversary it exists for: a tampered state that bothered to
    // recompute its own root and reseal its own digest. Both earlier gates are
    // satisfied and the supply is still wrong.
    auto payload = original;
    payload.total_supply += 1'000;
    reseal(payload);
    require_refusal(payload, parameters, ps::SnapshotV9Error::not_conserved,
                    "a resealed payload that issued value from nowhere");
  }
  {
    // **A timestamp with no month cannot reach gate 3, and the reason is worth
    // stating rather than discovering.** The kernel's first clock invariant says
    // the state's stamp must be inside `calendar-v1`'s accepted range, so the
    // obvious case here is a resealed payload carrying an out-of-range stamp.
    // It cannot be built: `state_root` refuses to compute a root over a stamp C1
    // would have refused, so there is nothing to reseal *with*.
    //
    // The consequence is that the restore refuses at **gate 1** instead — the
    // rebuilt ledger commits no root at all — and the conservation invariant is
    // unreachable through a snapshot rather than merely redundant with it. Both
    // halves are asserted, because the refusal alone would not say which gate
    // fired or why the other cannot.
    auto payload = original;
    payload.timestamp = v9::kMaxTimestampMillis + 1;

    v9::StateSummary summary;
    summary.chain_id = payload.chain_id;
    summary.height = payload.height;
    summary.timestamp = payload.timestamp;
    summary.supply_limit = payload.supply_limit;
    summary.total_supply = payload.total_supply;
    summary.fee_pool_balance = payload.fee_pool;
    pv::require(
        !v9::state_root(summary, payload.accounts, payload.economy).has_value(),
        "a stamp outside the accepted range must have no state root, which is "
        "what makes the conservation invariant unreachable from here");

    require_refusal(payload, parameters,
                    ps::SnapshotV9Error::state_root_mismatch,
                    "a payload whose timestamp has no month");
  }
}

void check_prefix_refusals(const Payload& original,
                           const ps::SnapshotParametersV9& parameters) {
  {
    auto payload = original;
    payload.magic[0] = 'X';
    require_refusal(payload, parameters, ps::SnapshotV9Error::malformed,
                    "a payload under another magic");
  }
  {
    // The magic is one family across every version, so an earlier payload is an
    // unsupported version rather than malformed input. Both neighbours are
    // named: version one because it is the other snapshot still in the tree, and
    // version eight because it is the one a stale deployment would still be
    // writing.
    auto payload = original;
    payload.version = 1;
    require_refusal(payload, parameters,
                    ps::SnapshotV9Error::unsupported_version,
                    "a version-one snapshot");
  }
  {
    auto payload = original;
    payload.version = 8;
    require_refusal(payload, parameters,
                    ps::SnapshotV9Error::unsupported_version,
                    "a version-eight snapshot");
  }
}

// The two cases that operate on the encoded octets rather than on the builder,
// because a builder always reseals and these are about the seal.
void check_digest_refusals(const Payload& original,
                           const ps::SnapshotParametersV9& parameters) {
  auto raw = original.encode();
  pv::require(raw.size() > 200, "the fixture payload is larger than its prefix");
  {
    auto mutated = raw;
    mutated[180] ^= 0x01U;
    const auto decoded = ps::decode_snapshot_v9(mutated, parameters);
    pv::require(std::holds_alternative<ps::SnapshotV9Error>(decoded) &&
                    std::get<ps::SnapshotV9Error>(decoded) ==
                        ps::SnapshotV9Error::digest_mismatch,
                "a payload with one flipped octet");
  }
  {
    // Shorter than the fixed prefix, root, and digest together, so nothing can
    // be read before the length check.
    const v9::Bytes truncated(raw.begin(), raw.begin() + 100);
    const auto decoded = ps::decode_snapshot_v9(truncated, parameters);
    pv::require(std::holds_alternative<ps::SnapshotV9Error>(decoded) &&
                    std::get<ps::SnapshotV9Error>(decoded) ==
                        ps::SnapshotV9Error::malformed,
                "a payload below the fixed size");
  }
}

}  // namespace

void verify_framing_refusals() {
  fixture::Signatures signatures;
  const auto scenario = fixture::settled_scenario(signatures);
  const auto parameters = ps::snapshot_parameters(scenario.ledger);
  const auto original = payload_of(scenario.ledger);

  check_prefix_refusals(original, parameters);
  check_digest_refusals(original, parameters);
  check_parameter_refusals(original, parameters);
  check_section_refusals(original, parameters);
  check_gate_refusals(original, parameters);

  // A suite that refuses everything proves nothing about any refusal, so the
  // unmutated payload has to restore.
  const auto raw = original.encode();
  const auto decoded = ps::decode_snapshot_v9(raw, parameters);
  pv::require(std::holds_alternative<ps::DecodedSnapshotV9>(decoded),
              "the refusal fixture's own payload must restore");
}

}  // namespace snapshot_v9_tests

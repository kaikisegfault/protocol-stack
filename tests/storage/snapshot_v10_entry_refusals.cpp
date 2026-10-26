// One case per value rule version nine added to the snapshot, and a sample of
// the fixed entries, carried to version ten.
//
// **This is `snapshot_v9_entry_refusals.cpp`'s sweep, moved rather than left
// behind**, because ADR 0104's last step deletes version nine's suite. Its
// subjects are version nine's four kinds, the widened pool value, and the
// settlement cursor in the fixed set, which version ten carries unchanged. A
// deletion that went by filename would have left each rule with no
// snapshot-level check at all, which is what ADR 0092 found once already.
// `snapshot_v10_inherited_refusals.cpp` carries version eight's sweep for the
// same reason, and `snapshot_v10_registry_refusals.cpp` holds what version ten
// adds.
//
// **The fixture is the version-ten chain**, which holds every kind these cases
// mutate, a monthly claim among them. Every case mutates one entry of a
// payload the module has already accepted.
//
// **Almost none of them reseals, and the reason is worth stating once.**
// Resealing carries a mutation *past* the earlier gates so it reaches the one
// under test. Every case here is refused by `apply_entry` or `complete`, which
// run **before** any gate, so a reseal would buy nothing. Worse, most of these
// payloads cannot be resealed at all: `economy_root` refuses an entry whose kind
// or width is not one a transition writes, so a mutation of exactly that shape
// leaves no root to seal with. The single case that must reach gate 3 reseals
// and says so at the point it does.

#include "snapshot_v10_fixture.hpp"

#include <string>
#include <variant>

namespace snapshot_v10_tests {
namespace {

// A refusal built by rewriting one entry's value. The entry is reached by kind,
// so a scenario change moves it without moving this test.
void refuse_value(const Payload& original,
                  const ps::SnapshotParametersV10& parameters, v10::Entry kind,
                  const std::string& subject,
                  void (*mutate)(v10::Bytes& value)) {
  auto payload = original;
  mutate(entry_of(payload, kind).value);
  require_refusal(payload, parameters, ps::SnapshotV10Error::invalid_state,
                  subject);
}

// --- the four kinds version nine added ----------------------------------------

void check_window_month(const Payload& original,
                        const ps::SnapshotParametersV10& parameters) {
  // A month index past the calendar. `decode_window_month_value` refuses it,
  // which is what keeps every derivation that reads a month total.
  refuse_value(original, parameters, v10::Entry::window_month,
               "a window month past the end of the calendar",
               [](v10::Bytes& value) {
                 poke_u32(value, 0, v10::kMaxMonthIndex + 1);
               });
  {
    // The window a month entry names is not bounded by this decoder on purpose —
    // which windows may hold an entry is a statement about the head's height,
    // and the kernel's retention invariant makes it at gate 3. This case proves
    // the statement is made somewhere rather than nowhere.
    auto payload = original;
    auto& entry = last_of(payload, v10::Entry::window_month);
    poke_u64(entry.key, 1, 1ULL << 40U);
    // The one case in this file that reseals, because it is the one that must
    // reach a gate rather than a decoder.
    reseal(payload);
    require_refusal(payload, parameters, ps::SnapshotV10Error::not_conserved,
                    "a window month entry outliving its retention");
  }
}

void check_monthly_figure(const Payload& original,
                          const ps::SnapshotParametersV10& parameters) {
  // A figure of zero seconds is a second encoding of absence: a candidate with
  // no entry has a figure of zero already. Admitting one would be the difference
  // between writing as many entries as ran and writing 100,000 every window.
  refuse_value(original, parameters, v10::Entry::monthly_uptime_figure,
               "a monthly figure of zero seconds",
               [](v10::Bytes& value) { poke_u64(value, 0, 0); });
  {
    // The month lives in the key, so the bound reaches this entry only because
    // the decoder rebuilds the key and compares it. Gate 3 would refuse it too,
    // one layer later and without naming the entry.
    auto payload = original;
    auto& entry = last_of(payload, v10::Entry::monthly_uptime_figure);
    poke_u32(entry.key, 1, v10::kMaxMonthIndex + 1);
    require_refusal(payload, parameters, ps::SnapshotV10Error::invalid_state,
                    "a monthly figure keyed to a month past the calendar");
  }
  {
    // Both writers of a seat-keyed entry resolve the seat from the seat table
    // first, so a figure naming a seat the chain never sold is a state no
    // transition produced.
    auto payload = original;
    auto& entry = last_of(payload, v10::Entry::monthly_uptime_figure);
    poke_u32(entry.key, 5, 900'000);
    require_refusal(payload, parameters, ps::SnapshotV10Error::invalid_state,
                    "a monthly figure naming a seat the chain never sold");
  }
}

void check_monthly_claim(const Payload& original,
                         const ps::SnapshotParametersV10& parameters) {
  // A claim is a balance and a balance of zero is absence, so a settlement whose
  // share rounds to zero writes no entry at all.
  refuse_value(original, parameters, v10::Entry::monthly_pool_claim,
               "a monthly claim that accrued nothing",
               [](v10::Bytes& value) { poke_u64(value, 0, 0); });
  // The referral balance's shape: `minted` follows `accrued` and never passes
  // it. A claim that minted more than it was awarded is value from nowhere.
  refuse_value(original, parameters, v10::Entry::monthly_pool_claim,
               "a monthly claim that minted more than it accrued",
               [](v10::Bytes& value) {
                 poke_u64(value, 0, 10);
                 poke_u64(value, 8, 11);
               });
  {
    auto payload = original;
    auto& entry = last_of(payload, v10::Entry::monthly_pool_claim);
    poke_u32(entry.key, 1, 900'000);
    require_refusal(payload, parameters, ps::SnapshotV10Error::invalid_state,
                    "a monthly claim naming a seat the chain never sold");
  }
}

void check_settlement_cursor(const Payload& original,
                             const ps::SnapshotParametersV10& parameters) {
  refuse_value(original, parameters, v10::Entry::settlement_cursor,
               "a settlement cursor past the end of the calendar",
               [](v10::Bytes& value) {
                 poke_u32(value, 0, v10::kMaxMonthIndex + 1);
               });
  {
    // **Version nine's addition to the fixed set, and version ten adds none.**
    // Genesis writes the cursor
    // and no transition removes it, so a payload without one describes a chain
    // that never opened. Without this check the restore would default the cursor
    // to zero and the roots would catch it a step later, as a mismatch with no
    // subject.
    auto payload = original;
    erase_kind(payload, v10::Entry::settlement_cursor);
    require_refusal(payload, parameters, ps::SnapshotV10Error::invalid_state,
                    "a payload with no settlement cursor");
  }
}

// --- the value version nine widened -------------------------------------------

void check_unreferred_pool(const Payload& original,
                           const ps::SnapshotParametersV10& parameters) {
  // The two identities stated over one entry. `payable` is what the pool has
  // received and not yet assigned, so it cannot exceed what it received.
  refuse_value(original, parameters, v10::Entry::unreferred_pool,
               "an unreferred pool owing more than it accrued",
               [](v10::Bytes& value) {
                 poke_u64(value, 0, 10);
                 poke_u64(value, 8, 11);
                 poke_u64(value, 16, 0);
               });
  // And what has been minted cannot exceed what is neither owed nor already
  // taken. This is the identity that catches a unit minted twice.
  refuse_value(original, parameters, v10::Entry::unreferred_pool,
               "an unreferred pool minting what it still owes",
               [](v10::Bytes& value) {
                 poke_u64(value, 0, 10);
                 poke_u64(value, 8, 6);
                 poke_u64(value, 16, 5);
               });
  {
    // **The width is the compatibility boundary and it is checked.** Version
    // eight's 16-octet value carries two of these three quantities, and the
    // dispatcher refuses it on width before any field order could be mistaken
    // for another.
    auto payload = original;
    auto& entry = entry_of(payload, v10::Entry::unreferred_pool);
    pv::require(entry.value.size() == 24,
                "version nine's unreferred pool value is 24 octets");
    entry.value.resize(16);
    require_refusal(payload, parameters, ps::SnapshotV10Error::invalid_state,
                    "a version-eight unreferred pool value");
  }
}

// --- a sample of the inherited rules ----------------------------------------

void check_inherited(const Payload& original,
                     const ps::SnapshotParametersV10& parameters) {
  // The identity's own index rule: a registration writes index 1 and count 1,
  // and a deletion lowers only the count.
  refuse_value(original, parameters, v10::Entry::hub_identity,
               "an identity whose next index is below its live count",
               [](v10::Bytes& value) {
                 poke_u32(value, 40, 1);
                 poke_u32(value, 44, 2);
               });
  refuse_value(original, parameters, v10::Entry::seat,
               "a seat flag that is neither zero nor one",
               [](v10::Bytes& value) { value[32] = 2; });
  // Entry kind 8 keeps version six's name and holds the launch key, which the
  // prefix carries too, so a disagreement is two chains' keys in one payload.
  refuse_value(original, parameters, v10::Entry::verifier_key,
               "a launch key entry that disagrees with the prefix",
               [](v10::Bytes& value) { value[0] ^= 0xFFU; });
  refuse_value(original, parameters, v10::Entry::verified_user_counter,
               "more enrolled identities than the population admits",
               [](v10::Bytes& value) {
                 poke_u64(value, 0, v10::kVerifiedUserPopulation + 1);
               });
  {
    // The **last** channel entry, not the first: raising an index makes the key
    // larger, and moving the first one past its siblings would break the strict
    // order the section is also required to be in, so the refusal would come
    // from the ordering rule instead of the one under test.
    auto payload = original;
    auto& entry = last_of(payload, v10::Entry::channel);
    entry.key[1] = static_cast<std::uint8_t>(v10::kChannelCount);
    require_refusal(payload, parameters, ps::SnapshotV10Error::invalid_state,
                    "a channel index no manifest defines");
  }
  {
    auto payload = original;
    erase_kind(payload, v10::Entry::recovery_pool);
    require_refusal(payload, parameters, ps::SnapshotV10Error::invalid_state,
                    "a payload with no recovery pool entry");
  }
  {
    auto payload = original;
    auto& entry = last_of(payload, v10::Entry::seat);
    poke_u32(entry.key, 1, v10::kMaxSeatId + 1);
    require_refusal(payload, parameters, ps::SnapshotV10Error::invalid_state,
                    "a seat past the founder capacity");
  }
  {
    // A kind the contract does not define at all, refused before any width or
    // value rule is consulted.
    auto payload = original;
    v10::EconomyEntry entry;
    entry.key = {0xFEU, 0x00U};
    entry.value = {};
    payload.economy.push_back(entry);
    require_refusal(payload, parameters, ps::SnapshotV10Error::invalid_state,
                    "an entry of a kind the contract does not define");
  }
}

}  // namespace

void verify_entry_refusals(const Fixtures& fixtures) {
  const auto& ledger = fixtures.chain.ledger;
  const auto parameters = ps::snapshot_parameters(ledger);
  const auto original = payload_of(ledger);

  // Every case below reaches for one of these by kind, so their presence is
  // required once here rather than discovered as a confusing failure inside a
  // mutation. **Every missing kind is reported together**, because a loop that
  // stopped at the first would turn one scenario change into as many rounds of
  // diagnosis as there are kinds it moved.
  std::string missing;
  for (const auto kind :
       {v10::Entry::window_month, v10::Entry::monthly_uptime_figure,
        v10::Entry::monthly_pool_claim, v10::Entry::settlement_cursor,
        v10::Entry::unreferred_pool, v10::Entry::hub_identity, v10::Entry::seat,
        v10::Entry::channel, v10::Entry::verifier_key,
        v10::Entry::verified_user_counter, v10::Entry::recovery_pool}) {
    auto payload = original;
    if (find_entry(payload, kind) == payload.economy.end()) {
      missing += (missing.empty() ? "" : ", ") +
                 std::to_string(static_cast<unsigned>(kind));
    }
  }
  pv::require(missing.empty(),
              "the refusal fixture carries no entry of kind " + missing);

  check_window_month(original, parameters);
  check_monthly_figure(original, parameters);
  check_monthly_claim(original, parameters);
  check_settlement_cursor(original, parameters);
  check_unreferred_pool(original, parameters);
  check_inherited(original, parameters);

  const auto raw = original.encode();
  const auto decoded = ps::decode_snapshot_v10(raw, parameters);
  pv::require(std::holds_alternative<ps::DecodedSnapshotV10>(decoded),
              "each refusal fixture's own payload must restore");
}

}  // namespace snapshot_v10_tests

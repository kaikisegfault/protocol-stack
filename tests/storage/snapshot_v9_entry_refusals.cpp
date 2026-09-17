// One case per value rule the entry decoders enforce, weighted toward what
// version nine adds.
//
// **The inherited kinds get a sample rather than a sweep.** Their rules are
// version eight's, unchanged, and `storage_snapshot_v8_tests` holds the full
// set; what a sample establishes here is that the port did not lose them. What
// gets the sweep is the four kinds version nine adds, its widened pool value,
// and its new fixed entry — the surfaces this slice had to write from nothing.
//
// Every case mutates one entry of a payload the module has already accepted, and
// every case that changes a value **reseals**, so the refusal comes from the
// decoder rather than from a root that stopped matching. A case that did not
// reseal would pass for the wrong reason on any rule the decoder later dropped.

#include "snapshot_v9_fixture.hpp"

#include <string>
#include <variant>

namespace snapshot_v9_tests {
namespace {

// A refusal built by rewriting one entry's value and resealing. The entry is
// reached by kind, so a scenario change moves it without moving this test.
void refuse_value(const Payload& original,
                  const ps::SnapshotParametersV9& parameters, v9::Entry kind,
                  const std::string& subject,
                  void (*mutate)(v9::Bytes& value)) {
  auto payload = original;
  mutate(entry_of(payload, kind).value);
  reseal(payload);
  require_refusal(payload, parameters, ps::SnapshotV9Error::invalid_state,
                  subject);
}

// --- the four kinds version nine adds ---------------------------------------

void check_window_month(const Payload& original,
                        const ps::SnapshotParametersV9& parameters) {
  // A month index past the calendar. `decode_window_month_value` refuses it,
  // which is what keeps every derivation that reads a month total.
  refuse_value(original, parameters, v9::Entry::window_month,
               "a window month past the end of the calendar",
               [](v9::Bytes& value) {
                 poke_u32(value, 0, v9::kMaxMonthIndex + 1);
               });
  {
    // The window a month entry names is not bounded by this decoder on purpose —
    // which windows may hold an entry is a statement about the head's height,
    // and the kernel's retention invariant makes it at gate 3. This case proves
    // the statement is made somewhere rather than nowhere.
    auto payload = original;
    auto& entry = last_of(payload, v9::Entry::window_month);
    poke_u64(entry.key, 1, 1ULL << 40U);
    reseal(payload);
    require_refusal(payload, parameters, ps::SnapshotV9Error::not_conserved,
                    "a window month entry outliving its retention");
  }
}

void check_monthly_figure(const Payload& original,
                          const ps::SnapshotParametersV9& parameters) {
  // A figure of zero seconds is a second encoding of absence: a candidate with
  // no entry has a figure of zero already. Admitting one would be the difference
  // between writing as many entries as ran and writing 100,000 every window.
  refuse_value(original, parameters, v9::Entry::monthly_uptime_figure,
               "a monthly figure of zero seconds",
               [](v9::Bytes& value) { poke_u64(value, 0, 0); });
  {
    // The month lives in the key, so the bound reaches this entry only because
    // the decoder rebuilds the key and compares it. Gate 3 would refuse it too,
    // one layer later and without naming the entry.
    auto payload = original;
    auto& entry = last_of(payload, v9::Entry::monthly_uptime_figure);
    poke_u32(entry.key, 1, v9::kMaxMonthIndex + 1);
    reseal(payload);
    require_refusal(payload, parameters, ps::SnapshotV9Error::invalid_state,
                    "a monthly figure keyed to a month past the calendar");
  }
  {
    // Both writers of a seat-keyed entry resolve the seat from the seat table
    // first, so a figure naming a seat the chain never sold is a state no
    // transition produced.
    auto payload = original;
    auto& entry = last_of(payload, v9::Entry::monthly_uptime_figure);
    poke_u32(entry.key, 5, 900'000);
    reseal(payload);
    require_refusal(payload, parameters, ps::SnapshotV9Error::invalid_state,
                    "a monthly figure naming a seat the chain never sold");
  }
}

void check_monthly_claim(const Payload& original,
                         const ps::SnapshotParametersV9& parameters) {
  // A claim is a balance and a balance of zero is absence, so a settlement whose
  // share rounds to zero writes no entry at all.
  refuse_value(original, parameters, v9::Entry::monthly_pool_claim,
               "a monthly claim that accrued nothing",
               [](v9::Bytes& value) { poke_u64(value, 0, 0); });
  // The referral balance's shape: `minted` follows `accrued` and never passes
  // it. A claim that minted more than it was awarded is value from nowhere.
  refuse_value(original, parameters, v9::Entry::monthly_pool_claim,
               "a monthly claim that minted more than it accrued",
               [](v9::Bytes& value) {
                 poke_u64(value, 0, 10);
                 poke_u64(value, 8, 11);
               });
  {
    auto payload = original;
    auto& entry = last_of(payload, v9::Entry::monthly_pool_claim);
    poke_u32(entry.key, 1, 900'000);
    reseal(payload);
    require_refusal(payload, parameters, ps::SnapshotV9Error::invalid_state,
                    "a monthly claim naming a seat the chain never sold");
  }
}

void check_settlement_cursor(const Payload& original,
                             const ps::SnapshotParametersV9& parameters) {
  refuse_value(original, parameters, v9::Entry::settlement_cursor,
               "a settlement cursor past the end of the calendar",
               [](v9::Bytes& value) {
                 poke_u32(value, 0, v9::kMaxMonthIndex + 1);
               });
  {
    // **Version nine's addition to the fixed set.** Genesis writes the cursor
    // and no transition removes it, so a payload without one describes a chain
    // that never opened. Without this check the restore would default the cursor
    // to zero and the roots would catch it a step later, as a mismatch with no
    // subject.
    auto payload = original;
    erase_kind(payload, v9::Entry::settlement_cursor);
    reseal(payload);
    require_refusal(payload, parameters, ps::SnapshotV9Error::invalid_state,
                    "a payload with no settlement cursor");
  }
}

// --- the value version nine widens ------------------------------------------

void check_unreferred_pool(const Payload& original,
                           const ps::SnapshotParametersV9& parameters) {
  // The two identities stated over one entry. `payable` is what the pool has
  // received and not yet assigned, so it cannot exceed what it received.
  refuse_value(original, parameters, v9::Entry::unreferred_pool,
               "an unreferred pool owing more than it accrued",
               [](v9::Bytes& value) {
                 poke_u64(value, 0, 10);
                 poke_u64(value, 8, 11);
                 poke_u64(value, 16, 0);
               });
  // And what has been minted cannot exceed what is neither owed nor already
  // taken. This is the identity that catches a unit minted twice.
  refuse_value(original, parameters, v9::Entry::unreferred_pool,
               "an unreferred pool minting what it still owes",
               [](v9::Bytes& value) {
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
    auto& entry = entry_of(payload, v9::Entry::unreferred_pool);
    pv::require(entry.value.size() == 24,
                "version nine's unreferred pool value is 24 octets");
    entry.value.resize(16);
    reseal(payload);
    require_refusal(payload, parameters, ps::SnapshotV9Error::invalid_state,
                    "a version-eight unreferred pool value");
  }
}

// --- a sample of the inherited rules ----------------------------------------

void check_inherited(const Payload& original,
                     const ps::SnapshotParametersV9& parameters) {
  // **Not the referral balance**, which version eight's suite uses for this
  // shape: the version-nine trace purchases every seat with `has_referrer`
  // clear, so no kind-4 entry exists to mutate. The identity's own index rule is
  // the equivalent inherited case over an entry this trace does produce.
  refuse_value(original, parameters, v9::Entry::hub_identity,
               "an identity whose next index is below its live count",
               [](v9::Bytes& value) {
                 poke_u32(value, 40, 1);
                 poke_u32(value, 44, 2);
               });
  refuse_value(original, parameters, v9::Entry::seat,
               "a seat flag that is neither zero nor one",
               [](v9::Bytes& value) { value[32] = 2; });
  refuse_value(original, parameters, v9::Entry::verifier_key,
               "a verifier key entry that disagrees with the prefix",
               [](v9::Bytes& value) { value[0] ^= 0xFFU; });
  refuse_value(original, parameters, v9::Entry::verified_user_counter,
               "more enrolled identities than the population admits",
               [](v9::Bytes& value) {
                 poke_u64(value, 0, v9::kVerifiedUserPopulation + 1);
               });
  {
    // The **last** channel entry, not the first: raising an index makes the key
    // larger, and moving the first one past its siblings would break the strict
    // order the section is also required to be in, so the refusal would come
    // from the ordering rule instead of the one under test.
    auto payload = original;
    auto& entry = last_of(payload, v9::Entry::channel);
    entry.key[1] = static_cast<std::uint8_t>(v9::kChannelCount);
    reseal(payload);
    require_refusal(payload, parameters, ps::SnapshotV9Error::invalid_state,
                    "a channel index no manifest defines");
  }
  {
    auto payload = original;
    erase_kind(payload, v9::Entry::recovery_pool);
    reseal(payload);
    require_refusal(payload, parameters, ps::SnapshotV9Error::invalid_state,
                    "a payload with no recovery pool entry");
  }
  {
    auto payload = original;
    auto& entry = last_of(payload, v9::Entry::seat);
    poke_u32(entry.key, 1, v9::kMaxSeatId + 1);
    reseal(payload);
    require_refusal(payload, parameters, ps::SnapshotV9Error::invalid_state,
                    "a seat past the founder capacity");
  }
  {
    // A kind the contract does not define at all, refused before any width or
    // value rule is consulted.
    auto payload = original;
    v9::EconomyEntry entry;
    entry.key = {0xFEU, 0x00U};
    entry.value = {};
    payload.economy.push_back(entry);
    reseal(payload);
    require_refusal(payload, parameters, ps::SnapshotV9Error::invalid_state,
                    "an entry of a kind the contract does not define");
  }
}

}  // namespace

void verify_entry_refusals() {
  fixture::Signatures signatures;
  const auto scenario = fixture::settled_scenario(signatures);
  const auto parameters = ps::snapshot_parameters(scenario.ledger);
  const auto original = payload_of(scenario.ledger);

  // Every case below reaches for one of these by kind, so their presence is
  // required once here rather than discovered as a confusing failure inside a
  // mutation. **Every missing kind is reported together**, because a loop that
  // stopped at the first would turn one scenario change into as many rounds of
  // diagnosis as there are kinds it moved.
  std::string missing;
  for (const auto kind :
       {v9::Entry::window_month, v9::Entry::monthly_uptime_figure,
        v9::Entry::monthly_pool_claim, v9::Entry::settlement_cursor,
        v9::Entry::unreferred_pool, v9::Entry::hub_identity, v9::Entry::seat,
        v9::Entry::channel, v9::Entry::verifier_key,
        v9::Entry::verified_user_counter, v9::Entry::recovery_pool}) {
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
  const auto decoded = ps::decode_snapshot_v9(raw, parameters);
  pv::require(std::holds_alternative<ps::DecodedSnapshotV9>(decoded),
              "each refusal fixture's own payload must restore");
}

}  // namespace snapshot_v9_tests

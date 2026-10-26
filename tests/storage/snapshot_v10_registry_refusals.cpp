// One case per rule a restore applies to the four entry kinds version ten adds.
//
// **Three layers refuse them, and each case names its layer.**
//
// - **A value no encoder writes** is refused by the kernel's own decoder, as
//   `invalid_state`: a machine key written at height 0, a retirement at height
//   0, a founder count of 0 or above the limit. These mutate payload octets and
//   do not reseal, because `apply_entry` runs before any gate.
// - **A state the registry invariants forbid** is refused at gate 3, as
//   `not_conserved`. These mutate the typed ledger and project it, so the
//   payload is resealed by construction. Each also requires the named
//   invariant to be among `conservation_failures`, because the error code alone
//   would not say which invariant fired, and a case caught by a different rule
//   than the one it names establishes nothing about its own.
// - **The retirement's single-height rule** is the snapshot's own, refused in
//   `complete` as `invalid_state`. Each such case also requires that
//   `conservation_failures` finds nothing, which is what shows the rule is not
//   redundant with gate 3: invariant 7 is about two heights and cannot run here.
//
// Two fixtures carry the kinds. The chain holds two machine keys, their owners,
// and Alice's founder count, with no retirement. The population holds 101
// machines, all active at its head, and the retirement.

#include "snapshot_v10_fixture.hpp"

#include <algorithm>
#include <string>
#include <string_view>
#include <variant>

namespace snapshot_v10_tests {
namespace {

using Error = ps::SnapshotV10Error;

void require_failure(const v10::Ledger& ledger, std::string_view invariant,
                     const std::string& subject) {
  const auto failures = v10::conservation_failures(ledger);
  pv::require(std::find(failures.begin(), failures.end(), invariant) !=
                  failures.end(),
              subject + ": expected the invariant \"" + std::string(invariant) +
                  "\" to fail");
}

// A ledger mutated in its typed maps, projected, and refused at gate 3 under
// the named invariant.
void refuse_unconserved(const v10::Ledger& ledger,
                        const ps::SnapshotParametersV10& parameters,
                        std::string_view invariant, const std::string& subject) {
  require_failure(ledger, invariant, subject);
  require_refusal(payload_of(ledger), parameters, Error::not_conserved, subject);
}

// A ledger every conservation invariant accepts, refused or restored by the
// retirement rule alone.
void require_conserved(const v10::Ledger& ledger, const std::string& subject) {
  pv::require(v10::conservation_failures(ledger).empty(),
              subject + ": the state is conserved, so gate 3 cannot decide it");
}

// --- kind 24, the machine key ------------------------------------------------

void check_machine_keys(const v10::Ledger& chain,
                        const ps::SnapshotParametersV10& parameters) {
  {
    // The value no kind-23 transaction writes: every one executes at a height
    // of at least 1.
    auto payload = payload_of(chain);
    poke_u64(entry_of(payload, v10::Entry::machine_key).value, 64, 0);
    require_refusal(payload, parameters, Error::invalid_state,
                    "a machine key registered at height 0");
  }
  // Invariant 1, at both of its conditions. Bob's machine key and its owner
  // entry are moved together, so the inverse still holds and only the seat is
  // wrong: first to his seat that was bought and never activated, then to a
  // seat nobody bought.
  for (const auto& [seat_id, subject] :
       {std::pair{std::uint32_t{2}, "a machine key on a seat never activated"},
        std::pair{std::uint32_t{7}, "a machine key on a seat nobody bought"}}) {
    auto ledger = chain;
    const auto entry = ledger.machine_keys.at(1);
    ledger.machine_keys.erase(1);
    ledger.machine_keys.emplace(seat_id, entry);
    ledger.machine_key_owners[entry.machine_public_key] = seat_id;
    refuse_unconserved(ledger, parameters,
                       "a machine key names a seat that is not activated", subject);
  }
  {
    // Invariant 3. One key on two seats cannot have an owner entry for both,
    // so invariant 2 fails beside it; the case names the one it is about.
    auto ledger = chain;
    ledger.machine_keys.at(1).machine_public_key =
        ledger.machine_keys.at(0).machine_public_key;
    refuse_unconserved(ledger, parameters, "two machine-key entries hold the same key",
                       "one machine key on two seats");
  }
  {
    // Invariant 4. Alice's machine carries the latest assigned window, so one
    // more is a window the chain has not assigned.
    auto ledger = chain;
    const auto assigned = v10::last_assigned_window(ledger.height);
    pv::require(assigned && ledger.machine_keys.at(0).last_met_window == *assigned,
                "Alice's machine is marked for the latest assigned window");
    ledger.machine_keys.at(0).last_met_window = *assigned + 1;
    refuse_unconserved(ledger, parameters,
                       "a machine was marked for a window not yet assigned",
                       "a machine marked for a window not yet assigned");
  }
}

// --- kind 26, the inverse -----------------------------------------------------

void check_owners(const v10::Ledger& chain,
                  const ps::SnapshotParametersV10& parameters) {
  const auto alice_key = chain.machine_keys.at(0).machine_public_key;
  {
    // Invariant 2 from the owner's side: an owner entry naming another seat.
    auto ledger = chain;
    ledger.machine_key_owners.at(alice_key) = 1;
    refuse_unconserved(ledger, parameters,
                       "an owner entry names a seat that does not hold its key",
                       "an owner entry naming the wrong seat");
  }
  {
    // And from the machine's side: a machine key with no owner entry, which is
    // the state in which the key could be registered on a second seat.
    auto ledger = chain;
    ledger.machine_key_owners.erase(alice_key);
    refuse_unconserved(ledger, parameters,
                       "a machine key has no owner entry naming its seat",
                       "a machine key with no owner entry");
  }
  {
    // An owner entry for a key no machine holds, which is what a replacement
    // that kept the old key's entry would leave behind.
    auto ledger = chain;
    ledger.machine_key_owners.emplace(fixture::machine_key(0, 8), 0);
    refuse_unconserved(ledger, parameters,
                       "an owner entry names a seat that does not hold its key",
                       "an owner entry for a released key");
  }
  {
    // The width is the dispatcher's, before any decoder runs.
    auto payload = payload_of(chain);
    entry_of(payload, v10::Entry::machine_key_owner).value.push_back(0);
    require_refusal(payload, parameters, Error::invalid_state,
                    "an owner entry five octets wide");
  }
}

// --- kind 27, the founder count -----------------------------------------------

void check_founder_counts(const v10::Ledger& chain,
                          const ps::SnapshotParametersV10& parameters) {
  // Invariant 6 is the decoder's here, because the decoder refuses both values
  // by asking the encoder: 0 is a second encoding of absence, and the limit is
  // checked before a count is written.
  for (const auto& [count, subject] :
       {std::pair{std::uint32_t{0}, "a founder count of zero"},
        std::pair{v10::kFounderRegistrationsPerWindow + 1,
                  "a founder count above the limit"}}) {
    auto payload = payload_of(chain);
    poke_u32(entry_of(payload, v10::Entry::founder_registrations).value, 8, count);
    require_refusal(payload, parameters, Error::invalid_state, subject);
  }
  pv::require(chain.founder_registrations.size() == 1,
              "the chain holds one founder count");
  const auto founder = chain.founder_registrations.begin()->first;
  {
    // Invariant 5: a count taken in a window the head has not reached.
    auto ledger = chain;
    ledger.founder_registrations.at(founder).registration_window =
        v10::window_of_height(ledger.height) + 1;
    refuse_unconserved(ledger, parameters,
                       "a founder counted registrations for a future window",
                       "a founder count for a future window");
  }
  {
    // Invariant 8, which is what bounds the founder entries by the seats: a
    // count naming an identity that owns no seat with a machine key.
    auto ledger = chain;
    const auto entry = ledger.founder_registrations.at(founder);
    ledger.founder_registrations.erase(founder);
    ledger.founder_registrations.emplace(fixture::repeated(0x77), entry);
    refuse_unconserved(ledger, parameters,
                       "a founder count names an identity with no machine key",
                       "a founder count for an identity with no machine");
  }
}

// --- kind 25, the retirement --------------------------------------------------

v10::Ledger retired_at(const v10::Ledger& ledger, std::optional<std::uint64_t> height) {
  auto mutated = ledger;
  mutated.launch_retired_at = height;
  return mutated;
}

void check_retirement(const v10::Ledger& chain, const v10::Ledger& cutoff,
                      const ps::SnapshotParametersV10& chain_parameters,
                      const ps::SnapshotParametersV10& parameters) {
  const auto recorded = cutoff.launch_retired_at;
  pv::require(recorded.has_value(), "the population retired the launch key");
  {
    // **Refused twice over, and the test cannot say which.** The decoder
    // refuses a zero, because it would be a second encoding of absence, and no
    // assignment is at height 0, so the rule below refuses it too. A probe that
    // replaced the decoder with a raw read passed here for that reason. The
    // decoder's own rule is pinned where it is the only one,
    // `state.launch_retirement_refuses_zero` in the codec target.
    auto payload = payload_of(cutoff);
    poke_u64(entry_of(payload, v10::Entry::launch_retirement).value, 0, 0);
    require_refusal(payload, parameters, Error::invalid_state,
                    "a retirement at height 0");
  }
  // **The case the rule exists for.** Every machine is active at the head, so
  // the latest registry step counted 101 and wrote the retirement, and a
  // payload without it would let the launch key sign again. A seeded network
  // restores it on every replica and agrees with itself (ADR 0097), so no peer
  // would catch it.
  const auto dropped = retired_at(cutoff, std::nullopt);
  require_conserved(dropped, "a dropped retirement");
  require_refusal(payload_of(dropped), parameters, Error::invalid_state,
                  "a retirement dropped while 101 machines are active");

  // A retirement only a registry step could have written: at an assignment
  // that assigned a window of at least 1, at or below the head.
  for (const auto& [height, subject] :
       {std::pair{*recorded + 1, "a retirement between assignments"},
        std::pair{2 * v10::kCycleBlocks, "a retirement at the window-0 assignment"},
        std::pair{cutoff.height + v10::kCycleBlocks, "a retirement above the head"}}) {
    const auto moved = retired_at(cutoff, height);
    require_conserved(moved, subject);
    require_refusal(payload_of(moved), parameters, Error::invalid_state, subject);
  }
  // The control: another assignment height inside the rule restores, so the
  // rule refuses the heights it names and not every height but the recorded one.
  require_restores(payload_of(retired_at(cutoff, 3 * v10::kCycleBlocks)), parameters,
                   "a retirement at the window-1 assignment");

  // A retirement on a chain that never marked 100 machines.
  const auto unearned = retired_at(chain, 3 * v10::kCycleBlocks);
  require_conserved(unearned, "an unearned retirement");
  require_refusal(payload_of(unearned), chain_parameters, Error::invalid_state,
                  "a retirement with two machines ever marked");

  // **What one height cannot show.** Two machines marked one window earlier
  // leave 99 active, which is a population whose count fell after it retired.
  // With the retirement it restores, and **without it it restores too**: a
  // chain that never retired could hold the same state, so dropping it here is
  // the two-height fact a snapshot cannot see, and only the source chain's root
  // exposes it. The pair pins the rule's extent, so a stricter rule that
  // refused any absent retirement with 100 machines marked would fail here, and
  // would be wrong: 101 machines can each have met some window without 100
  // having met the same one.
  auto fell = cutoff;
  const auto assigned = v10::last_assigned_window(fell.height);
  pv::require(assigned.has_value(), "the population's head has an assigned window");
  for (const std::uint32_t seat_id : {0U, 1U}) {
    fell.machine_keys.at(seat_id).last_met_window = *assigned - 1;
  }
  require_restores(payload_of(fell), parameters, "a retirement after the count fell");
  require_restores(payload_of(retired_at(fell, std::nullopt)), parameters,
                   "a retirement dropped after the count fell");
}

}  // namespace

void verify_registry_refusals(const Fixtures& fixtures) {
  const auto& chain = fixtures.chain.ledger;
  const auto& cutoff = fixtures.cutoff.ledger;
  const auto chain_parameters = ps::snapshot_parameters(chain);
  const auto parameters = ps::snapshot_parameters(cutoff);
  pv::require(chain.machine_keys.size() == 2 && !chain.launch_retired_at,
              "the chain holds two machine keys and no retirement");
  require_restores(payload_of(chain), chain_parameters, "the chain's own payload");
  require_restores(payload_of(cutoff), parameters, "the population's own payload");

  check_machine_keys(chain, chain_parameters);
  check_owners(chain, chain_parameters);
  check_founder_counts(chain, chain_parameters);
  check_retirement(chain, cutoff, chain_parameters, parameters);
}

}  // namespace snapshot_v10_tests

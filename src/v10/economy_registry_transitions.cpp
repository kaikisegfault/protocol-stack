// Everything version ten adds to execution: kind 23, kind 10's attester, the
// registry step, and the seven invariants.
//
// **This is the one execution translation unit version nine does not have**, so
// the difference between the two kernels' execution is this file plus the edits
// the contract forces in five others: kind 10's restated conditions, the
// approval message every body-carried kind verifies over, the lifetime rule
// straight after `EXPIRED`, the registry step's place in the prologue, and the
// projection and the gate that see the three new entries.
//
// Each transition is stated as its ordered rejection conditions and its writes,
// over exactly the state it reads, and validates completely before it writes.
// So a refusal leaves the state untouched without a rollback, which
// `execute_block` requires by re-deriving the state root across every failure.

#include "economy_ledger_internal.hpp"

#include <set>

namespace protocol::v10 {

bool machine_active(const Ledger& ledger, std::uint32_t seat_id) {
  const auto entry = ledger.machine_keys.find(seat_id);
  if (entry == ledger.machine_keys.end()) return false;
  // A mark of 0 means none, and is never active: no seat is in scope in window
  // 0, so no window-0 assignment can mark a machine (ADR 0103).
  if (entry->second.last_met_window == 0) return false;
  const auto assigned = last_assigned_window(ledger.height);
  return assigned && entry->second.last_met_window == *assigned;
}

bool retirement_kept(const std::optional<std::uint64_t>& before,
                     const Ledger& after) {
  return !before || after.launch_retired_at == before;
}

namespace internal {
namespace {

Outcome refused(Result result) { return Outcome{result, 0, 0}; }

}  // namespace

// Kind 23. **The HUB approval is always required, and the posture does not
// waive it.** Installing a key that can admit people is authority over the
// ecosystem rather than movement of the founder's own value, and the
// constitution requires an accepted signature and a fresh biometric approval
// together for a sensitive Founder action. So a stolen signer key cannot install
// a rogue verifier on a founder's seat.
//
// **A replacement keeps the count and the mark.** Activity belongs to the
// seat's cycle rather than to the key, so a machine that replaces its key
// mid-window stays active, and a count that reset would let key rotation bypass
// ADR 0101's limit. Replacing a key is how a founder retires a compromised one;
// nothing else in this version revokes a key.
std::optional<Outcome> register_machine_key(Ledger& ledger,
                                            const Envelope& envelope,
                                            const Body& body,
                                            const Octets32& escrow,
                                            const SignatureVerifier& verify) {
  // Conditions 1 to 4: range, purchased, activated, and owned by the identity
  // behind the acting escrow, in the order kinds 3 and 4 apply to a seat.
  const auto check = require_seat(ledger, body.seat_id, escrow, true);
  if (check.refusal) return refused(*check.refusal);

  // Condition 5, for any seat including this one: one key serves one seat.
  if (ledger.machine_key_owners.contains(body.machine_public_key)) {
    return refused(Result::replay);
  }
  // Condition 6. The attestation binds the transaction's own validity, so the
  // two expire together and the lifetime rule has already bounded both.
  const auto attestation =
      attestation_message(ledger.chain_id, body.seat_id, body.machine_public_key,
                          body.build_digest, envelope.valid_until_height);
  if (!verify(ledger.build_authority_key, attestation, body.attestation_signature)) {
    return refused(Result::unauthorized);
  }
  // Condition 7, against the recorded HUB key of the seat's identity, which
  // condition 4 has just required to own the acting escrow.
  if (confirmation_field_is_absent(body.hub_signature)) {
    return refused(Result::biometric_required);
  }
  const auto approval = approval_message(envelope);
  // Kind 23 is an approval kind and its body decoded at execution, so an absent
  // message is a disagreement inside one codec rather than a result.
  if (!approval) return std::nullopt;
  const auto& identity = ledger.seats.at(body.seat_id).hub_identity_hash;
  if (!verify_hub_signature(ledger, identity, *approval, body.hub_signature,
                            verify)) {
    return refused(Result::unauthorized);
  }

  const auto existing = ledger.machine_keys.find(body.seat_id);
  if (existing == ledger.machine_keys.end()) {
    MachineKey written;
    written.machine_public_key = body.machine_public_key;
    written.build_digest = body.build_digest;
    written.registered_at_height = ledger.height;
    ledger.machine_keys.emplace(body.seat_id, written);
  } else {
    ledger.machine_key_owners.erase(existing->second.machine_public_key);
    existing->second.machine_public_key = body.machine_public_key;
    existing->second.build_digest = body.build_digest;
    existing->second.registered_at_height = ledger.height;
  }
  ledger.machine_key_owners[body.machine_public_key] = body.seat_id;
  return charged(ledger, escrow);
}

// Kind 10's conditions 3 and 4. The registration message binds the attesting
// seat, so one machine's signature cannot be presented as another's, and each
// registration counts against the limit of the machine that actually signed.
//
// **The limit is checked after the signature**, so a refusal for the limit is
// only ever given for a registration that was otherwise valid. A forgery naming
// a full machine is `UNAUTHORIZED`, which is the true reason. **The launch key
// has no limit**: ADR 0101 makes it the only signer until it retires, and a
// limit would only slow the launch.
Attestation check_attester(const Ledger& ledger, const Envelope& envelope,
                           const Body& body, const SignatureVerifier& verify) {
  const auto seat_id = body.attesting_seat_id;
  const auto message = registration_message(
      ledger.chain_id, seat_id, body.hub_identity_hash,
      envelope.authority_public_key, body.first_signer_public_key,
      envelope.valid_until_height);
  if (seat_id == kLaunchAttester) {
    if (ledger.launch_retired_at) return Attestation{Result::launch_key_retired, {}};
    if (!verify(ledger.launch_key, message, body.attestation_signature)) {
      return Attestation{Result::unauthorized, {}};
    }
    return Attestation{};
  }

  if (seat_id > kMaxSeatId) return Attestation{Result::cycle_range, {}};
  const auto entry = ledger.machine_keys.find(seat_id);
  if (entry == ledger.machine_keys.end()) {
    return Attestation{Result::machine_key_not_found, {}};
  }
  if (!machine_active(ledger, seat_id)) {
    return Attestation{Result::machine_not_active, {}};
  }
  if (!verify(entry->second.machine_public_key, message,
              body.attestation_signature)) {
    return Attestation{Result::unauthorized, {}};
  }
  // The count belongs to the window it was taken in, so a stored count from an
  // earlier window is a count of zero in this one.
  const auto window = window_of_height(ledger.height);
  const auto count = entry->second.registration_window == window
                         ? entry->second.registrations_in_window
                         : std::uint32_t{0};
  if (count >= kMachineRegistrationsPerWindow) {
    return Attestation{Result::registration_limit, {}};
  }
  auto counted = entry->second;
  counted.registration_window = window;
  counted.registrations_in_window = count + 1;
  return Attestation{std::nullopt, counted};
}

// The registry step, at an assignment height, after the figure accumulation and
// before the due window's kind-19 entries are deleted.
//
// **Version nine does not hold the fact this step records.** The assignment
// record's `accrued` bit means met, in span, and under the cap, and its `winner`
// bit means won, and the window's uptime records are deleted in this same
// prologue. So the step marks the seats that have a machine key before the
// evidence goes. "Met" is the uptime test, whatever the accumulation cap or the
// seat's span says, because ADR 0101 reads the answer as the uptime record.
//
// **The count excludes a mark of 0** (ADR 0103). Zero means none, and the due
// window is 0 at the window-0 assignment, where no seat is in scope and nothing
// can be marked; counting it would have every unmarked key meet window 0, and a
// hundred keys registered in the first two windows would retire the launch key
// before any machine had met a cycle. **The count is computed, never stored**,
// because every machine it counts has just been marked.
//
// **Retirement happens here and nowhere else**, because the cutoff is a count of
// machines that met a cycle and that count changes only when a cycle is
// assigned. Once written it is never removed, so a later fall below the cutoff
// never revives the launch key.
RegistryStep registry_step(Ledger& ledger, std::uint64_t due,
                           std::span<const SeatCycle> measured) {
  // Both sequences are in ascending seat order, so one merge walks the
  // machine-key entries in the order the specification states.
  auto seat = measured.begin();
  for (auto& [seat_id, entry] : ledger.machine_keys) {
    while (seat != measured.end() && seat->seat_id < seat_id) ++seat;
    if (seat == measured.end()) break;
    if (seat->seat_id == seat_id &&
        seat->uptime_seconds >= kActivityThresholdSeconds) {
      entry.last_met_window = due;
    }
  }

  RegistryStep step;
  for (const auto& [seat_id, entry] : ledger.machine_keys) {
    (void)seat_id;
    if (entry.last_met_window != 0 && entry.last_met_window == due) {
      step.active_machines += 1;
    }
  }
  if (!ledger.launch_retired_at &&
      step.active_machines >= kLaunchRetirementActiveMachines) {
    ledger.launch_retired_at = ledger.height;
    step.retired = true;
  }
  return step;
}

// Invariants 1 through 6, stated over the typed registry the projection
// encodes. The inverse is a map of its own, so invariant 2 compares two things
// the state holds rather than one thing with itself.
std::vector<std::string_view> registry_failures(const Ledger& ledger) {
  std::vector<std::string_view> failures;
  const auto assigned = last_assigned_window(ledger.height);
  const auto window = window_of_height(ledger.height);
  std::set<Octets32> held;
  for (const auto& [seat_id, entry] : ledger.machine_keys) {
    // 1. Every machine-key entry's seat is purchased and activated.
    const auto seat = ledger.seats.find(seat_id);
    if (seat == ledger.seats.end() || !seat->second.is_activated) {
      failures.push_back("a machine key names a seat that is not activated");
    }
    // 2, first half: every machine-key entry's key has an owner entry naming
    //    its seat.
    const auto owner = ledger.machine_key_owners.find(entry.machine_public_key);
    if (owner == ledger.machine_key_owners.end() || owner->second != seat_id) {
      failures.push_back("a machine key has no owner entry naming its seat");
    }
    // 3. No two machine-key entries hold the same key.
    if (!held.insert(entry.machine_public_key).second) {
      failures.push_back("two machine-key entries hold the same key");
    }
    // 4. Every mark is 0 or at most the most recently assigned window.
    if (entry.last_met_window != 0 &&
        (!assigned || entry.last_met_window > *assigned)) {
      failures.push_back("a machine was marked for a window not yet assigned");
    }
    // 5. Every count belongs to this window or an earlier one.
    if (entry.registration_window > window) {
      failures.push_back("a machine counted registrations for a future window");
    }
    // 6. No count exceeds the limit.
    if (entry.registrations_in_window > kMachineRegistrationsPerWindow) {
      failures.push_back("a machine signed more registrations than its limit");
    }
  }
  // 2, second half: every owner entry names a seat whose entry holds its key.
  for (const auto& [key, seat_id] : ledger.machine_key_owners) {
    const auto entry = ledger.machine_keys.find(seat_id);
    if (entry == ledger.machine_keys.end() ||
        entry->second.machine_public_key != key) {
      failures.push_back("an owner entry names a seat that does not hold its key");
    }
  }
  return failures;
}

}  // namespace internal
}  // namespace protocol::v10

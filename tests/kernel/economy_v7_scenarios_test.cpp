// The five recorded version-seven scenarios, rebuilt transaction for transaction.
//
// Each is chosen for what would go undetected otherwise:
//
// 1. **pool** — two seats, a cycle nobody wins whose whole contribution enters
//    the recovery pool, a cycle one seat wins that absorbs the pool entire, and
//    a real kind-4 mint that collects both. It ends with `outstanding` at zero
//    and the pool at zero on every Founder Node channel: 100% of what the
//    manifest promised for those cycles reached a beneficiary, where version six
//    would have left four base permissions in a carry nothing ever releases.
// 2. **boundary** — the same chain at the same height under the rejected
//    ordering, where the mint runs before the assignment. Under version six that
//    block was merely expensive; under version seven it is rejected whole,
//    because the window's permissions enter `outstanding` with the only seat
//    that could have claimed them already marked past them.
// 3. **permanence** — a machine past its own 731 issuance cycles, contributing
//    nothing and eligible for everything. A cycle with no contributing seat at
//    all drains the pool to it, and it mints. That is the case that would strand
//    the pool forever if a later reader narrowed the winner set to the
//    contributing set.
// 4. **carried** — every kind version seven leaves alone, executed under version
//    seven. **The bytes are version six's and the commitments are not**: a
//    registration under version seven is byte-for-byte a registration under
//    version six, lands in a different state root, and produces a different
//    receipt, and nothing anywhere fixed either until this scenario did.
// 5. **referral** — kind 5, the last kind version seven admits that nothing else
//    here reaches. The prologue accrues the referral leg to an identity and that
//    identity mints it in the same block.

#include "economy_v7_execution_fixture.hpp"

namespace economy_v7_execution {
namespace {

Scenario open_scenario(const std::string& name) {
  Scenario scenario;
  scenario.name = name;
  scenario.ledger = open_trace_ledger();
  return scenario;
}

void note(Scenario& scenario, const std::string& name, std::uint64_t value) {
  scenario.notes[name] = std::to_string(value);
}

void note_true(Scenario& scenario, const std::string& name, bool value) {
  pv::require(value, scenario.name + ": " + name);
  scenario.notes[name] = "true";
}

// A recorded five-leg figure, one vector per channel, which is the shape the
// file uses because each leg has its own destination and its own cap.
void note_legs(Scenario& scenario, const std::string& name,
               const v7::RecoveryPool& pool) {
  for (std::size_t index = 0; index < v7::kRecoveryPoolLegs; ++index) {
    note(scenario, name + ".channel" + std::to_string(index), pool[index]);
  }
}

v7::RecoveryPool node_legs(const std::array<std::uint64_t, v7::kChannelCount>& values) {
  v7::RecoveryPool node{};
  for (std::size_t index = 0; index < v7::kRecoveryPoolLegs; ++index) {
    node[index] = values[index];
  }
  return node;
}

v7::RecoveryPool claimable_of(const Scenario& scenario) {
  const auto owed = v7::claimable(scenario.ledger);
  pv::require(owed.has_value(), scenario.name + ": claimable derives");
  return *owed;
}

bool is_zero(const v7::RecoveryPool& pool) {
  for (const auto amount : pool) {
    if (amount != 0) return false;
  }
  return true;
}

// Every figure the vectors record about one assigned window, taken from the
// derivation the block actually performed.
void note_window(Scenario& scenario, const v7::BlockOutcome& block) {
  pv::require(block.assignment.has_value(),
              scenario.name + ": the block derived an assignment");
  const auto& derived = *block.assignment;
  const auto prefix = "window" + std::to_string(derived.cycle_window) + ".";
  const auto record = scenario.ledger.assignments.find(derived.cycle_window);
  pv::require(record != scenario.ledger.assignments.end(),
              scenario.name + ": the window has a record");
  const auto decoded = v7::decode_cycle_assignment_value(record->second);
  pv::require(decoded.has_value(), scenario.name + ": the record decodes");

  note(scenario, prefix + "winner_count", decoded->winner_count);
  note(scenario, prefix + "reallocated_count", decoded->reallocated_count);
  note(scenario, prefix + "in_scope_count", decoded->in_scope_count);
  note(scenario, prefix + "bitmap_bits", decoded->bitmap_bits);
  note(scenario, prefix + "contributing_count", derived.contributing_count);
  note(scenario, prefix + "eligible_count", derived.eligible_count);
  note_legs(scenario, prefix + "pool_after", derived.pool_after);
  note_legs(scenario, prefix + "pool_absorbed", decoded->pool_absorbed);
  scenario.notes[prefix + "record"] = hex(record->second);
  // Step 6 reads the pool before step 7 writes it, so what a cycle absorbed is
  // exactly what it found — never what it found plus the dust it then produced.
  bool absorbed_before = true;
  for (std::size_t index = 0; index < v7::kRecoveryPoolLegs; ++index) {
    const auto expected =
        decoded->winner_count == 0 ? 0 : derived.pool_before[index];
    absorbed_before =
        absorbed_before && decoded->pool_absorbed[index] == expected;
  }
  note_true(scenario, prefix + "absorbed_before_the_cycle_contributed_its_own_dust",
            absorbed_before);
}

struct Person {
  const Octets32& identity;
  const Octets32& key;
  const Octets32& signer_key;
  std::uint32_t seat_id;
  const char* name;
};

// Register each person, sell each a seat, and activate every seat.
//
// Three blocks: the registrations, the purchases, and — after a run of empty
// blocks — the activations at a height inside the window before the first
// assignable one. Every fee is paid out of the entry airdrop the registration
// itself issued, which is the property version six established and version seven
// inherits without restating it.
Scenario seated_chain(Signatures& signatures, const std::string& name,
                      const std::vector<Person>& people,
                      std::uint64_t first_window) {
  auto scenario = open_scenario(name);
  auto& ledger = scenario.ledger;

  std::vector<Step> registrations;
  for (const auto& person : people) {
    registrations.push_back(
        {std::string(person.name) + "_registers",
         register_input(signatures, ledger, person.identity, person.key,
                        person.signer_key, kValidUntil)});
  }
  run(scenario, signatures, registrations);

  std::vector<Step> purchases;
  for (const auto& person : people) {
    purchases.push_back({std::string(person.name) + "_purchases",
                         purchase_input(signatures, ledger, person.identity,
                                        person.key, person.signer_key,
                                        person.seat_id, 1)});
  }
  run(scenario, signatures, purchases);

  advance_to(scenario, activation_height(first_window) - 1);

  std::vector<Step> activations;
  for (const auto& person : people) {
    activations.push_back({std::string(person.name) + "_activates",
                           activate_input(signatures, ledger, person.identity,
                                          person.key, person.signer_key,
                                          person.seat_id, 2)});
  }
  run(scenario, signatures, activations);
  return scenario;
}

// The same registration bytes a version-six chain would admit, refused here
// because every signed message binds a chain ID derived under a version-seven
// label. The two are alternative chains rather than a sequence.
Bytes version_six_registration(Signatures& signatures, const v7::Ledger& ledger) {
  v7::Ledger foreign = ledger;
  // Version six's chain identity over the same genesis, which differs from
  // version seven's only in the label and the schema version inside it.
  foreign.chain_id = Octets32{};
  return register_input(signatures, foreign, kCarolIdentity, kCarolKey,
                        kCarolSignerKey, kValidUntil);
}

// Nobody meets the dead cycle; Alice alone meets the won one, so she accrues her
// own permission, takes Bob's reallocated one, and absorbs everything the dead
// cycle left.
v7::UptimeSchedule pool_uptime() {
  v7::UptimeSchedule uptime;
  uptime[kDeadWindow] = {{kAliceSeat, kFailedUptimeSeconds, true},
                         {kBobSeat, kFailedUptimeSeconds, true}};
  uptime[kWonWindow] = {{kAliceSeat, kMetUptimeSeconds, true},
                        {kBobSeat, kFailedUptimeSeconds, true}};
  return uptime;
}

// Alice is in span and fails the cycle; Carol is past her own 731 cycles and
// also fails it, so nobody wins and Alice's whole contribution enters the pool.
// At the drained window Alice's machine is out of scope entirely, so the
// contributing set is empty and nothing is assigned — and Carol still wins.
v7::UptimeSchedule permanence_uptime() {
  v7::UptimeSchedule uptime;
  uptime[kStrandedWindow] = {{kAliceSeat, kFailedUptimeSeconds, true},
                             {kCarolSeat, kFailedUptimeSeconds, false}};
  uptime[kDrainedWindow] = {{kCarolSeat, kMetUptimeSeconds, false}};
  return uptime;
}

}  // namespace

Scenario pool_scenario(Signatures& signatures) {
  auto scenario = seated_chain(
      signatures, "pool",
      {{kAliceIdentity, kAliceKey, kAliceSignerKey, kAliceSeat, "alice"},
       {kBobIdentity, kBobKey, kBobSignerKey, kBobSeat, "bob"}},
      kDeadWindow);
  auto& ledger = scenario.ledger;
  const auto uptime = pool_uptime();

  advance_to_boundary(scenario, kDeadWindow);
  const auto& dead = run(scenario, signatures, {}, &uptime);
  pv::require(dead.assigned_window == kDeadWindow, "the dead cycle is assigned");
  note(scenario, "dead_window", *dead.assigned_window);
  note_window(scenario, dead);
  note_legs(scenario, "pool_after_dead_cycle", ledger.pool);
  const auto outstanding_after_dead = node_legs(ledger.channel_outstanding);
  note_legs(scenario, "outstanding_after_dead_cycle", outstanding_after_dead);
  const auto owed_after_dead = claimable_of(scenario);
  note_legs(scenario, "claimable_after_dead_cycle", owed_after_dead);
  // A cycle nobody won moved its whole contribution into the pool and left
  // nobody owed anything, which under version six would have been two silent
  // remainders in a term nothing ever releases.
  note_true(scenario, "a_cycle_nobody_won_left_its_whole_contribution_in_the_pool",
            ledger.pool == outstanding_after_dead);
  note_true(scenario, "a_cycle_nobody_won_owed_nobody_anything",
            is_zero(owed_after_dead));

  advance_to_boundary(scenario, kWonWindow);
  const auto& won = run(
      scenario, signatures,
      {// Alice collects both cycles: her own accrual, Bob's reallocated
       // permission, and the whole pool the dead cycle left behind.
       {"alice_mints",
        node_mint_input(signatures, ledger, kAliceIdentity, kAliceKey,
                        kAliceSignerKey, kAliceSeat, kAliceEscrow, 3)},
       // Bob generated two base permissions and met neither cycle, so his mint
       // succeeds, collects nothing, and pays a fee. The reallocation is what it
       // says it is.
       {"bob_mints_nothing",
        node_mint_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey,
                        kBobSeat, kBobEscrow, 3)},
       // A second mint in the same block. The mark now equals the last assigned
       // window, so the walk range is empty — which is the rule ADR 0045 derived
       // rather than the literal equality the text states.
       {"alice_mints_again",
        node_mint_input(signatures, ledger, kAliceIdentity, kAliceKey,
                        kAliceSignerKey, kAliceSeat, kAliceEscrow, 4)},
       {"carol_registers_on_the_version_six_chain",
        version_six_registration(signatures, ledger), false}},
      &uptime);
  pv::require(won.assigned_window == kWonWindow, "the won cycle is assigned");
  note(scenario, "won_window", *won.assigned_window);
  note_window(scenario, won);

  const auto pool_after_mint = ledger.pool;
  const auto outstanding_after_mint = node_legs(ledger.channel_outstanding);
  const auto issued_after_mint = node_legs(ledger.channel_issued);
  note_legs(scenario, "pool_after_mint", pool_after_mint);
  note_legs(scenario, "outstanding_after_mint", outstanding_after_mint);
  note_legs(scenario, "issued_after_mint", issued_after_mint);
  note(scenario, "minted_total_atomic",
       won.executed.front().outcome.issued_atomic);
  note(scenario, "assigned_permissions", ledger.assigned_permissions);
  note(scenario, "alice_mark", ledger.seats.at(kAliceSeat).minted_through_window);
  note(scenario, "bob_mark", ledger.seats.at(kBobSeat).minted_through_window);
  note(scenario, "unreferred_pool_atomic", ledger.pool_accrued);
  note(scenario, "verified_user_issued_atomic",
       ledger.channel_issued[v7::kVerifiedUserChannel]);

  // **The claim this whole version exists for.** `outstanding` is zero and the
  // pool is zero on every Founder Node channel, and `issued` equals exactly what
  // the manifest promised for the cycles assigned. Under version six the same
  // schedule leaves four base permissions in a carry nothing ever releases.
  bool everything_reached_a_beneficiary = is_zero(pool_after_mint) &&
                                          is_zero(outstanding_after_mint);
  for (std::uint8_t channel = 0; channel < v7::kRecoveryPoolLegs; ++channel) {
    everything_reached_a_beneficiary =
        everything_reached_a_beneficiary &&
        issued_after_mint[channel] ==
            ledger.assigned_permissions * v7::base_permission_leg(channel);
  }
  note_true(scenario,
            "every_unit_the_manifest_promised_for_these_cycles_reached_a_beneficiary",
            everything_reached_a_beneficiary);
  return scenario;
}

// The same block under both readings, on two copies of one state.
//
// The accepted reading is the pool scenario's. This one rebuilds the identical
// chain and offers the identical block with the assignment written **after** the
// transactions, which is the reading version six had to reject by argument.
Scenario boundary_scenario(Signatures& signatures) {
  auto scenario = seated_chain(
      signatures, "boundary",
      {{kAliceIdentity, kAliceKey, kAliceSignerKey, kAliceSeat, "alice"},
       {kBobIdentity, kBobKey, kBobSignerKey, kBobSeat, "bob"}},
      kDeadWindow);
  auto& ledger = scenario.ledger;
  const auto uptime = pool_uptime();

  advance_to_boundary(scenario, kDeadWindow);
  run(scenario, signatures, {}, &uptime);
  advance_to_boundary(scenario, kWonWindow);

  const Step mint{"alice_mints",
                  node_mint_input(signatures, ledger, kAliceIdentity, kAliceKey,
                                  kAliceSignerKey, kAliceSeat, kAliceEscrow, 3)};

  const auto before = v7::ledger_state_root(ledger);
  pv::require(before.has_value(), "the pre-block root derives");
  scenario.notes["state_root_before_the_boundary_block"] = hex(*before);

  // Under version seven the rejected ordering is not merely expensive, it is
  // unconstructible: the window's permissions enter `outstanding` while the only
  // seat that could have claimed them is already marked past them, so
  // `claimable + recovery_pool` falls short and the backing identity refuses the
  // block whole with the pre-block state preserved.
  v7::Ledger rejected = ledger;
  const auto refused = v7::execute_block(rejected, std::vector<Bytes>{mint.raw},
                                         signatures.verifier(), &uptime, false);
  note_true(scenario, "the_rejected_ordering_produces_no_block", !refused.has_value());
  const auto preserved = v7::ledger_state_root(rejected);
  note_true(scenario, "the_rejected_block_preserved_the_pre_block_state",
            preserved.has_value() && *preserved == *before);

  // **Which** identity refuses it, channel by channel. `execute_block` restores
  // the pre-block state and reports no reason, so the same ordering is rebuilt on
  // a second copy that is never rolled back and the shortfall is read off it.
  v7::Ledger shown = ledger;
  shown.height += 1;
  const auto admitted = v7::admit(mint.raw, shown.chain_id, signatures.verifier());
  pv::require(admitted.admitted(), "the mint is admitted under either ordering");
  pv::require(v7::execute(shown, admitted.transaction.envelope,
                          signatures.verifier())
                  .has_value(),
              "the mint executes under either ordering");
  const auto late = v7::derive_assignment(shown, kWonWindow, uptime.at(kWonWindow));
  pv::require(late.has_value() && v7::apply_assignment(shown, *late),
              "the late assignment applies");
  const auto owed = v7::claimable(shown);
  pv::require(owed.has_value(), "claimable derives on the rejected ordering");
  for (std::uint8_t channel = 0; channel < v7::kRecoveryPoolLegs; ++channel) {
    note_true(scenario,
              "the_rejected_ordering_breaks_channel" + std::to_string(channel) +
                  "_backing_identity",
              (*owed)[channel] + shown.pool[channel] !=
                  shown.channel_outstanding[channel]);
  }

  const auto& accepted = run(
      scenario, signatures,
      {mint,
       // The same refusal the pool scenario records, kept here so this
       // scenario's atomicity claim is about a refusal it actually saw.
       {"alice_mints_again",
        node_mint_input(signatures, ledger, kAliceIdentity, kAliceKey,
                        kAliceSignerKey, kAliceSeat, kAliceEscrow, 4)}},
      &uptime);
  const auto issued = accepted.executed.front().outcome.issued_atomic;
  note(scenario, "the_accepted_ordering_issued", issued);
  std::uint64_t base_permission = 0;
  for (std::uint8_t channel = 0; channel < v7::kRecoveryPoolLegs; ++channel) {
    base_permission += v7::base_permission_leg(channel);
  }
  // One ordering pays whole base permissions and the other pays nothing at all,
  // which is the cost version six could only argue about.
  note_true(scenario, "the_two_orderings_differ_by_a_whole_mint",
            issued != 0 && issued % base_permission == 0 && !refused.has_value());
  return scenario;
}

Scenario permanence_scenario(Signatures& signatures) {
  auto scenario = seated_chain(
      signatures, "permanence",
      {{kAliceIdentity, kAliceKey, kAliceSignerKey, kAliceSeat, "alice"},
       {kCarolIdentity, kCarolKey, kCarolSignerKey, kCarolSeat, "carol"}},
      kStrandedWindow);
  auto& ledger = scenario.ledger;
  const auto uptime = permanence_uptime();

  advance_to_boundary(scenario, kStrandedWindow);
  const auto& stranded = run(scenario, signatures, {}, &uptime);
  pv::require(stranded.assigned_window == kStrandedWindow,
              "the stranded cycle is assigned");
  note(scenario, "stranded_window", *stranded.assigned_window);
  note_window(scenario, stranded);
  note_legs(scenario, "pool_after_stranded_cycle", ledger.pool);

  advance_to_boundary(scenario, kDrainedWindow);
  const auto& drained = run(
      scenario, signatures,
      {{"carol_mints",
        node_mint_input(signatures, ledger, kCarolIdentity, kCarolKey,
                        kCarolSignerKey, kCarolSeat, kCarolEscrow, 3)},
       {"carol_mints_again",
        node_mint_input(signatures, ledger, kCarolIdentity, kCarolKey,
                        kCarolSignerKey, kCarolSeat, kCarolEscrow, 4)}},
      &uptime);
  pv::require(drained.assigned_window == kDrainedWindow,
              "the drained cycle is assigned");
  note(scenario, "drained_window", *drained.assigned_window);
  note_window(scenario, drained);
  note_legs(scenario, "pool_after_mint", ledger.pool);
  note_legs(scenario, "issued_after_mint", node_legs(ledger.channel_issued));
  const auto carol_issued = drained.executed.front().outcome.issued_atomic;
  note(scenario, "carol_issued_atomic", carol_issued);
  note(scenario, "assigned_permissions", ledger.assigned_permissions);

  // The drained cycle has no contributing seat at all: it assigns nothing and
  // still pays out the whole pool. That is ADR 0049's rule 3 — the 731 cycles
  // bound the distribution and not the machine's operating life — and it is the
  // case that would strand the pool forever if a later reader narrowed the
  // winner set to the contributing set.
  pv::require(drained.assignment.has_value(), "the drained cycle derived");
  note_true(scenario, "the_drained_cycle_assigned_no_permission_at_all",
            drained.assignment->contributing_count == 0);
  note_true(scenario, "a_cycle_with_no_contributing_seat_still_drained_the_pool",
            drained.assignment->contributing_count == 0 &&
                !is_zero(drained.assignment->pool_absorbed) &&
                is_zero(ledger.pool));
  note_true(scenario, "a_winner_was_outside_the_contributing_set",
            drained.assignment->winners.size() == 1 &&
                drained.assignment->winners.front() == kCarolSeat &&
                drained.assignment->contributing_count == 0);

  // Alice generated the permission Carol collected and never accrued a bit for
  // it, because she failed the cycle she was in span for.
  const auto stranded_record = ledger.assignments.at(kStrandedWindow);
  const auto decoded = v7::decode_cycle_assignment_value(stranded_record);
  pv::require(decoded.has_value(), "the stranded record decodes");
  note_true(scenario, "the_seat_that_generated_the_permission_never_accrued_a_bit",
            !v7::bit_is_set(decoded->accrued_bitmap, kAliceSeat) &&
                decoded->reallocated_count == 1);

  std::uint64_t base_permission = 0;
  for (std::uint8_t channel = 0; channel < v7::kRecoveryPoolLegs; ++channel) {
    base_permission += v7::base_permission_leg(channel);
  }
  note_true(scenario, "an_out_of_span_machine_collected_a_whole_base_permission",
            carol_issued == base_permission);
  return scenario;
}

Scenario carried_scenario(Signatures& signatures) {
  auto scenario = open_scenario("carried");
  auto& ledger = scenario.ledger;

  run(scenario, signatures,
      {{"alice_registers",
        register_input(signatures, ledger, kAliceIdentity, kAliceKey,
                       kAliceSignerKey, kValidUntil)},
       {"bob_registers",
        register_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey,
                       kValidUntil)}});

  // Kinds 1, 19, and 6. The default posture requires a confirmation at every
  // amount, so the unconfirmed transfer is refused and the confirmed one is not;
  // a refusal advances no nonce, which is why the confirmed transfer reuses 1.
  v7::Body direct;
  direct.channel_id = 5;
  direct.beneficiary_escrow_id = kAliceEscrow;
  direct.amount_atomic = 1;
  run(scenario, signatures,
      {{"alice_transfers_unconfirmed",
        transfer_input(signatures, ledger, kAliceSignerKey, 1, kBobEscrow,
                       kTransferAmount)},
       {"alice_transfers_confirmed",
        confirmed_transfer_input(signatures, ledger, 1, kBobEscrow,
                                 kTransferAmount, kAliceIdentity, kAliceKey,
                                 kAliceSignerKey, kAliceEscrow)},
       {"alice_transfers_to_an_unregistered_recipient",
        confirmed_transfer_input(signatures, ledger, 2, kAcceptedRecipient,
                                 kTransferAmount, kAliceIdentity, kAliceKey,
                                 kAliceSignerKey, kAliceEscrow)},
       {"alice_attempts_a_direct_issue",
        build(signatures, ledger, static_cast<std::uint8_t>(v7::Kind::direct_issue),
              kAliceSignerKey, 2, direct)}});

  // Kinds 13, 14, 15, and 16 — the four an identity performs with no signer at
  // all, which is the recovery architecture ADR 0040 exists for.
  v7::Body create;
  create.hub_identity_hash = kAliceIdentity;
  create.fee_escrow_id = kAliceEscrow;
  v7::Body remove;
  remove.hub_identity_hash = kAliceIdentity;
  remove.fee_escrow_id = kAliceEscrow;
  remove.target_escrow_id = kAliceSecondEscrow;
  v7::Body add_signer;
  add_signer.hub_identity_hash = kAliceIdentity;
  add_signer.escrow_id = kAliceEscrow;
  add_signer.signer_public_key = kFreshSignerKey;
  v7::Body revoke_signer;
  revoke_signer.hub_identity_hash = kAliceIdentity;
  revoke_signer.escrow_id = kAliceEscrow;
  revoke_signer.signer_id = v7::signer_id(kFreshSignerKey);
  run(scenario, signatures,
      {{"alice_creates_a_second_escrow",
        build(signatures, ledger,
              static_cast<std::uint8_t>(v7::Kind::escrow_create), kAliceKey, 2,
              create)},
       {"alice_deletes_the_second_escrow",
        build(signatures, ledger,
              static_cast<std::uint8_t>(v7::Kind::escrow_delete), kAliceKey, 3,
              remove)},
       {"alice_assigns_a_fresh_signer",
        build(signatures, ledger, static_cast<std::uint8_t>(v7::Kind::signer_add),
              kAliceKey, 4, add_signer)},
       {"alice_revokes_the_fresh_signer",
        build(signatures, ledger,
              static_cast<std::uint8_t>(v7::Kind::signer_revoke), kAliceKey, 5,
              revoke_signer)}});

  // Kind 17, in both directions. The opening posture is the strictest one the
  // contract admits, so the first change can only be a relaxation — and a
  // relaxation is exactly what the HUB signature is required for.
  v7::Posture relaxed;
  relaxed.requires_confirmation = true;
  relaxed.min_amount_atomic = kPostureMinimum;
  v7::Posture tightened;
  tightened.requires_confirmation = true;
  const auto change = [&](std::uint64_t nonce, const v7::Posture& posture,
                          bool signed_) {
    return posture_input(signatures, ledger, nonce, posture, signed_,
                         kAliceIdentity, kAliceKey, kAliceSignerKey, kAliceEscrow);
  };
  run(scenario, signatures,
      {{"alice_relaxes_without_a_signature", change(6, relaxed, false)},
       {"alice_relaxes_her_posture", change(6, relaxed, true)},
       {"alice_tightens_her_posture", change(7, tightened, false)},
       {"alice_repeats_the_posture_she_holds", change(8, tightened, false)}});

  // Kind 18, forty windows after enrolment: thirty are collectable and the ten
  // older ones are forfeited, which is the cap doing what it is for.
  advance_to(scenario, kCollectionHeight - 1);
  const auto& collection = run(
      scenario, signatures,
      {{"alice_collects_thirty_windows",
        verified_user_mint_input(signatures, ledger, kAliceIdentity, 8,
                                 kAliceEscrow, kAliceKey, kAliceSignerKey)},
       {"alice_collects_again_immediately",
        verified_user_mint_input(signatures, ledger, kAliceIdentity, 9,
                                 kAliceEscrow, kAliceKey, kAliceSignerKey)}});
  const auto collected = collection.executed.front().outcome.issued_atomic;
  const auto daily = v7::verified_user_daily_atomic();
  pv::require(daily.has_value() && *daily != 0, "the verified-user rate derives");
  note(scenario, "collection_height", kCollectionHeight);
  note(scenario, "collected_atomic", collected);
  note(scenario, "collected_windows", collected / *daily);
  note(scenario, "alice_balance", ledger.registry.accounts.at(kAliceEscrow).balance);
  note(scenario, "bob_balance", ledger.registry.accounts.at(kBobEscrow).balance);
  note(scenario, "verified_user_issued",
       ledger.channel_issued[v7::kVerifiedUserChannel]);

  // A created escrow that was deleted and a signer that was revoked leave no
  // entry behind, so the four recovery transitions are reversible in state as
  // well as in intent.
  note_true(scenario, "a_created_escrow_and_a_revoked_signer_leave_no_entry_behind",
            !ledger.registry.escrows.contains(kAliceSecondEscrow) &&
                !ledger.registry.signers.contains(v7::signer_id(kFreshSignerKey)));
  // No seat is ever sold here, so no cycle is ever assigned and the recovery
  // pool never moves. Every one of these ten kinds is indifferent to it.
  note_true(scenario, "the_recovery_pool_is_untouched_by_a_chain_with_no_seat",
            is_zero(ledger.pool) && ledger.assignments.empty());
  return scenario;
}

Scenario referral_scenario(Signatures& signatures) {
  auto scenario = open_scenario("referral");
  auto& ledger = scenario.ledger;

  run(scenario, signatures,
      {{"alice_registers",
        register_input(signatures, ledger, kAliceIdentity, kAliceKey,
                       kAliceSignerKey, kValidUntil)},
       {"bob_registers",
        register_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey,
                       kValidUntil)}});
  run(scenario, signatures,
      {{"bob_purchases_a_seat_referring_alice",
        purchase_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey,
                       kBobSeat, 1, &kAliceEscrow)}});
  advance_to(scenario, activation_height(kReferredWindow) - 1);
  run(scenario, signatures,
      {{"bob_activates",
        activate_input(signatures, ledger, kBobIdentity, kBobKey, kBobSignerKey,
                       kBobSeat, 2)}});

  v7::UptimeSchedule uptime;
  uptime[kReferredWindow] = {{kBobSeat, kMetUptimeSeconds, true}};

  advance_to_boundary(scenario, kReferredWindow);
  const auto& assigned = run(
      scenario, signatures,
      {{"alice_mints_her_referral",
        referral_mint_input(signatures, ledger, kAliceIdentity, kAliceKey,
                            kAliceSignerKey, kAliceEscrow, 1)},
       {"alice_mints_it_again",
        referral_mint_input(signatures, ledger, kAliceIdentity, kAliceKey,
                            kAliceSignerKey, kAliceEscrow, 2)},
       {"bob_mints_a_referral_he_has_never_earned",
        referral_mint_input(signatures, ledger, kBobIdentity, kBobKey,
                            kBobSignerKey, kBobEscrow, 3)}},
      &uptime);
  pv::require(assigned.assigned_window == kReferredWindow,
              "the referred cycle is assigned");
  note(scenario, "referred_window", *assigned.assigned_window);
  note(scenario, "referral_issued", ledger.channel_issued[v7::kReferralChannel]);
  note(scenario, "referral_outstanding",
       ledger.channel_outstanding[v7::kReferralChannel]);
  note(scenario, "unreferred_pool_accrued", ledger.pool_accrued);
  note(scenario, "alice_balance", ledger.registry.accounts.at(kAliceEscrow).balance);
  // The referral leg has no winner split and therefore no remainder, which is
  // why the recovery pool has five legs rather than six.
  note_true(scenario, "the_referral_channel_has_no_recovery_pool_term",
            v7::base_permission_leg(v7::kReferralChannel) == 0 &&
                v7::kReferralChannel >= v7::kRecoveryPoolLegs && is_zero(ledger.pool));
  return scenario;
}

}  // namespace economy_v7_execution

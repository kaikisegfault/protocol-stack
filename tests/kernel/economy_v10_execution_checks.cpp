// Every recorded execution vector, checked against what the kernel did.
//
// **Outcomes are the kernel's and are compared, never assumed.** Each result is
// read from the receipt the kernel produced for the labelled step, each count
// from the block or window outcome that computed it, and each root from the
// ledger the run left. The vectors were agreed with an independent derivation
// that imports nothing from `simulation/`, so a match here is agreement among
// three sources rather than two.

#include "economy_v10_execution_fixture.hpp"

#include <algorithm>
#include <set>
#include <string_view>

namespace economy_v10_execution {
namespace {

constexpr std::array<std::string_view, 16> kRegistrations{
    "launch.alice_registers",
    "lifetime.kind_10_past_the_bound",
    "launch.a_registration_the_launch_key_did_not_sign",
    "kind_10.a_seat_with_no_machine_key",
    "kind_10.a_seat_above_the_range",
    "launch.bob_registers",
    "kind_10.an_identity_registered_twice",
    "kind_10.a_first_signer_already_assigned",
    "kind_10.an_active_machine_registers",
    "kind_10.an_inactive_machine",
    "kind_10.a_seat_with_no_machine_key_later",
    "kind_10.another_machines_signature_under_this_seat",
    "launch.still_signs_below_the_cutoff",
    "kind_10.the_count_restarts_in_the_next_window",
    "kind_10.the_replaced_key_signs_nothing",
    "kind_10.the_new_key_signs",
};

constexpr std::array<std::string_view, 11> kMachineKeys{
    "kind_23.a_seat_above_the_range",
    "kind_23.an_unpurchased_seat",
    "kind_23.an_unactivated_seat",
    "kind_23.another_identitys_seat",
    "kind_23.a_key_another_seat_holds",
    "kind_23.a_key_this_seat_holds",
    "kind_23.an_attestation_the_build_authority_did_not_sign",
    "kind_23.no_approval",
    "kind_23.another_persons_approval",
    "kind_23.bob_registers_his_machine",
    "kind_23.the_replacement",
};

// Each lifetime case, and whether its transaction carries a HUB proof.
struct LifetimeCase {
  std::string_view label;
  bool governed;
};

constexpr std::array<LifetimeCase, 5> kLifetimes{{
    {"lifetime.kind_2_past_the_bound", true},
    {"lifetime.kind_15_past_the_bound", true},
    {"lifetime.kind_15_at_the_bound", true},
    {"lifetime.a_transfer_with_no_proof_is_not_governed", false},
    {"lifetime.a_tightening_with_no_proof_is_not_governed", false},
}};

constexpr std::array<std::string_view, 4> kReplays{
    "replay.the_republished_relax",
    "replay.the_relax_resigned_under_a_new_nonce",
    "replay.the_reused_confirmation",
    "replay.the_confirmation_resigned_under_a_new_nonce",
};

constexpr std::array<std::uint8_t, 9> kApprovedKinds{2, 3, 4, 5, 17, 18, 19, 22, 23};

constexpr std::array<std::string_view, 5> kReceipts{
    "approval.kind_23",
    "kind_10.an_active_machine_registers",
    "kind_10.an_inactive_machine",
    "kind_10.a_seat_with_no_machine_key",
    "lifetime.kind_15_past_the_bound",
};

std::string chain_key(std::string_view label) {
  return "chain." + std::string(label);
}

const v10::ExecutedTransaction& executed_step(
    const std::map<std::string, v10::ExecutedTransaction>& executed,
    std::string_view label) {
  const auto found = executed.find(std::string(label));
  pv::require(found != executed.end(), "the chain executed no " + std::string(label));
  return found->second;
}

v10::DecodedTransaction decoded(const Chain& chain, std::string_view label) {
  const auto raw = chain.raw.find(std::string(label));
  pv::require(raw != chain.raw.end(), "the chain offered no " + std::string(label));
  auto transaction = v10::decode_signed(raw->second);
  pv::require(transaction.has_value(), std::string(label) + " decodes");
  return *transaction;
}

Bytes hub_field(const v10::Envelope& envelope) {
  const auto body = v10::decode_body(envelope.kind, envelope.body);
  pv::require(body.has_value(), "an offered body decodes");
  return body->hub_signature;
}

Bytes approval_of(const v10::Envelope& envelope) {
  const auto message = v10::approval_message(envelope);
  pv::require(message.has_value(), "an approval kind has an approval message");
  return *message;
}

std::string root_hex(const v10::Ledger& ledger) {
  const auto root = v10::ledger_state_root(ledger);
  pv::require(root.has_value(), "the state is committable");
  return hex(*root);
}

std::uint16_t read_u16(std::span<const std::uint8_t> raw, std::size_t offset) {
  pv::require(raw.size() >= offset + 2, "a field inside the bytes");
  return static_cast<std::uint16_t>((raw[offset] << 8U) | raw[offset + 1]);
}

void verify_outcomes(const pv::Values& values, const Chain& chain) {
  const auto executed = chain.executed();
  for (const auto label : kRegistrations) {
    agree(values, chain_key(label),
          result_name(executed_step(executed, label).outcome.result));
  }
  for (const auto label : kMachineKeys) {
    agree(values, chain_key(label),
          result_name(executed_step(executed, label).outcome.result));
  }
  for (const auto& [label, governed] : kLifetimes) {
    agree(values, chain_key(label),
          result_name(executed_step(executed, label).outcome.result));
    if (governed) continue;
    const auto transaction = decoded(chain, label);
    const auto height = chain.heights.at(std::string(label));
    expect_claim(values, chain_key(label) + ".validity_reaches_past_the_bound",
                 transaction.envelope.valid_until_height > height + kLifetime);
  }
  for (const auto label : kReplays) {
    agree(values, chain_key(label),
          result_name(executed_step(executed, label).outcome.result));
  }
}

void verify_approvals(const pv::Values& values, const Chain& chain,
                      const Signatures& signatures) {
  const auto executed = chain.executed();
  for (const auto kind : kApprovedKinds) {
    const auto label = "approval.kind_" + std::to_string(kind);
    const auto transaction = decoded(chain, label);
    pv::require(transaction.envelope.kind == kind, label + " carries its kind");
    const auto message = approval_of(transaction.envelope);
    agree(values, chain_key(label) + ".message_sha256", hex(pv::sha256(message)));
    expect_claim(values, chain_key(label) + ".signed_over_the_whole_transaction",
                 signatures.verifies(kAlice.hub_key, message,
                                     hub_field(transaction.envelope)));
    agree(values, chain_key(label),
          result_name(executed_step(executed, label).outcome.result));
  }
  const std::string label = "approval.a_version_nine_approval_is_refused";
  const auto transaction = decoded(chain, label);
  expect_claim(values, chain_key(label) + ".signs_another_message",
               !signatures.verifies(kBob.hub_key, approval_of(transaction.envelope),
                                    hub_field(transaction.envelope)));
  agree(values, chain_key(label),
        result_name(executed_step(executed, label).outcome.result));
}

void verify_registry(const pv::Values& values, const Chain& chain) {
  agree(values, "chain.audit.alice_challenged", chain.alice.challenged.size());
  expect_claim(values, "chain.audit.alice_answered_every_challenge",
               chain.alice.answered == chain.alice.challenged &&
                   chain.alice.left_at_a_stop.empty());
  // Bob answered nothing, so every slot he was challenged in during window 1 is
  // one the expiry step cleared.
  std::set<std::uint64_t> lost;
  for (const auto height : chain.bob.challenged) {
    if (v10::window_of_height(height) != 1) continue;
    lost.insert((height % v10::kCycleBlocks) / v10::kSlotBlocks);
  }
  agree(values, "chain.audit.bob_window_1_credited_slots",
        v10::kSlotsPerWindow - lost.size());
  agree(values, "chain.registry.alice_mark_after_window_1",
        chain.marks_after_the_first_assignment.at(0));
  agree(values, "chain.registry.bob_mark_after_window_1",
        chain.marks_after_the_first_assignment.at(1));
  for (const auto& [name, block] :
       {std::pair{std::string("first_assignment"), &chain.first_assignment},
        std::pair{std::string("second_assignment"), &chain.second_assignment}}) {
    pv::require(block->has_value(), "the chain recorded its " + name);
    const auto& outcome = **block;
    agree(values, "chain.registry." + name + ".height", outcome.height);
    pv::require(outcome.active_machines.has_value(),
                "an assignment height computes the count");
    agree(values, "chain.registry." + name + ".active_machines",
          *outcome.active_machines);
    agree(values, "chain.registry." + name + ".root",
          hex(outcome.resulting_state_root));
  }
  expect_claim(values, "chain.registry.launch_key_unretired",
               !chain.ledger.launch_retired_at.has_value());
}

void verify_entries(const pv::Values& values, const Chain& chain) {
  const auto& ledger = chain.ledger;
  for (const std::uint32_t seat : {0U, 1U}) {
    const auto value = v10::machine_key_value(ledger.machine_keys.at(seat));
    pv::require(value.has_value(), "a recorded machine key encodes");
    agree(values, "chain.entry.seat_" + std::to_string(seat), hex(*value));
  }
  expect_claim(values, "chain.entry.the_replaced_key_has_no_owner",
               !ledger.machine_key_owners.contains(machine_key(0)));
  const auto owner = ledger.machine_key_owners.find(machine_key(0, 1));
  expect_claim(values, "chain.entry.the_new_key_names_its_seat",
               owner != ledger.machine_key_owners.end() && owner->second == 0);
}

void verify_receipts(const pv::Values& values, const Chain& chain,
                     const pv::Values& version_nine) {
  const auto executed = chain.executed();
  for (const auto label : kReceipts) {
    const auto receipt = v10::encode_receipt(executed_step(executed, label).receipt);
    pv::require(receipt.has_value(), "a receipt encodes");
    agree(values, "chain.receipt." + std::string(label), hex(*receipt));
  }
  // Version nine refuses a receipt whose version field is not its own, and the
  // field is the only octet pair that separates the two layouts. So the claim is
  // established from the accepted file: version nine's receipts carry the version
  // it records, and this one carries 10 in that field.
  const auto receipt =
      v10::encode_receipt(executed_step(executed, "approval.kind_23").receipt);
  pv::require(receipt.has_value(), "a receipt encodes");
  const auto found = version_nine.find("identity.receipt_version");
  pv::require(found != version_nine.end(), "version nine records its receipt version");
  const auto nine_version = std::stoull(found->second);
  expect_claim(values, "chain.receipt.version_nine_refuses_a_version_ten_receipt",
               read_u16(*receipt, 4) == v10::kReceiptVersion &&
                   v10::kReceiptVersion != nine_version);
}

void verify_blocks(const pv::Values& values, const Chain& chain) {
  for (const auto& [name, block] :
       {std::pair{std::string("first_assignment"), &*chain.first_assignment},
        std::pair{std::string("last"), &chain.blocks.back()}}) {
    agree(values, "chain.block." + name + ".header", hex(block->header));
    agree(values, "chain.block." + name + ".block_id", hex(block->block_id));
  }
  std::uint64_t refused_registry = 0;
  std::uint64_t refused = 0;
  std::uint64_t atomic_failures = 0;
  for (const auto& block : chain.blocks) {
    atomic_failures += block.atomic_failures;
    for (const auto& transaction : block.executed) {
      if (transaction.outcome.succeeded()) continue;
      refused += 1;
      if (transaction.kind == static_cast<std::uint8_t>(v10::Kind::hub_register) ||
          transaction.kind ==
              static_cast<std::uint8_t>(v10::Kind::register_machine_key)) {
        refused_registry += 1;
      }
    }
  }
  agree(values, "chain.refusals_among_kinds_10_and_23", refused_registry);
  expect_claim(values, "chain.every_refusal_left_the_root_unchanged",
               refused != 0 && atomic_failures == refused);
  agree(values, "chain.final_root", root_hex(chain.ledger));
  agree(values, "chain.final_height", chain.ledger.height);
}

std::optional<v10::CycleAssignment> assignment_record(const v10::Ledger& ledger,
                                                      std::uint64_t window) {
  const auto found = ledger.assignments.find(window);
  if (found == ledger.assignments.end()) return std::nullopt;
  auto record = v10::decode_cycle_assignment_value(found->second);
  pv::require(record.has_value(), "a recorded assignment decodes");
  return record;
}

bool accrued(const v10::CycleAssignment& record, std::uint32_t seat_id) {
  return v10::bit_is_set(record.accrued_bitmap, seat_id);
}

void verify_cap(const pv::Values& values, const Harness& cutoff) {
  const auto& ledger = cutoff.ledger;
  // The seat's mark is its activation window, 0, so window 31 is the first it
  // cannot hold.
  const auto capped = v10::kMintAccumulationCap + 1;
  std::optional<std::uint64_t> first_capped;
  for (const auto& [window, raw] : ledger.assignments) {
    (void)raw;
    const auto record = assignment_record(ledger, window);
    if (window >= 1 && !accrued(*record, 0)) {
      first_capped = window;
      break;
    }
  }
  pv::require(first_capped == capped, "the cap is reached where it is stated");
  agree(values, "cap.first_capped_window", *first_capped);
  expect_claim(values, "cap.the_capped_cycle_accrued_nothing",
               !accrued(*assignment_record(ledger, capped), 0));
  agree(values, "cap.the_capped_machine_is_marked",
        ledger.machine_keys.at(0).last_met_window);
  agree(values, "cap.final_root", root_hex(ledger));
}

void verify_span(const pv::Values& values, const Harness& span) {
  const auto& ledger = span.ledger;
  const auto first = v10::first_cycle_window(v10::kCycleBlocks - 10);
  const auto last_span = first + v10::kIssuanceCyclesPerSeat - 1;
  std::uint64_t last_accrued = 0;
  for (const auto& [window, raw] : ledger.assignments) {
    (void)raw;
    if (accrued(*assignment_record(ledger, window), 0)) last_accrued = window;
  }
  pv::require(last_accrued == last_span, "the span ends where it is stated");
  agree(values, "span.last_span_window", last_accrued);
  const auto past = assignment_record(ledger, last_span + 1);
  expect_claim(values, "span.the_cycle_past_the_span_accrued_nothing",
               past.has_value() && !accrued(*past, 0));
  agree(values, "span.the_machine_is_marked_past_its_span",
        ledger.machine_keys.at(0).last_met_window);
  agree(values, "span.final_root", root_hex(ledger));
}

bool reports(const v10::Ledger& ledger, std::string_view failure) {
  const auto failures = v10::conservation_failures(ledger);
  return std::find(failures.begin(), failures.end(), failure) != failures.end();
}

}  // namespace

void verify_genesis(const pv::Values& values) {
  const auto genesis = trace_genesis();
  const auto bytes = v10::encode_genesis(genesis);
  pv::require(bytes.has_value(), "the trace genesis encodes");
  agree(values, "genesis.bytes", hex(*bytes));
  const auto identity = v10::chain_id(genesis);
  pv::require(identity.has_value(), "the trace genesis has a chain identity");
  agree(values, "genesis.chain_id", hex(*identity));
  pv::require(open_trace_ledger().chain_id == *identity,
              "the ledger opens under the genesis's chain identity");
}

void verify_chain(const pv::Values& values, const Chain& chain,
                  const Signatures& signatures, const pv::Values& version_nine) {
  verify_outcomes(values, chain);
  verify_approvals(values, chain, signatures);
  verify_registry(values, chain);
  verify_entries(values, chain);
  verify_receipts(values, chain, version_nine);
  verify_blocks(values, chain);
}

void verify_population(const pv::Values& values, const Harness& cutoff,
                       const Harness& span) {
  for (const std::uint64_t window : {2ULL, 3ULL, 4ULL, 5ULL, 6ULL,
                                     static_cast<unsigned long long>(kCapRunWindow)}) {
    const auto& outcome = cutoff.windows.at(window);
    pv::require(outcome.active_machines.has_value(),
                "an assignment height computes the count");
    agree(values,
          "cutoff.registry.window_" + std::to_string(window - 2) + "_count",
          *outcome.active_machines);
  }
  pv::require(cutoff.unmarked_at_the_window_0_assignment.has_value(),
              "the run observed the window-0 assignment");
  const auto unmarked = *cutoff.unmarked_at_the_window_0_assignment;
  agree(values, "cutoff.registry.unmarked_keys_at_the_window_0_assignment", unmarked);
  expect_claim(values, "cutoff.registry.unmarked_keys_alone_would_reach_the_cutoff",
               unmarked >= v10::kLaunchRetirementActiveMachines);
  pv::require(cutoff.ledger.launch_retired_at.has_value(), "the launch key retired");
  agree(values, "cutoff.registry.retired_at_height", *cutoff.ledger.launch_retired_at);
  std::uint64_t retirements = 0;
  for (const auto& [window, outcome] : cutoff.windows) {
    (void)window;
    if (outcome.retired) retirements += 1;
  }
  expect_claim(values, "cutoff.registry.retired_exactly_once", retirements == 1);

  for (const auto& [label, result] : cutoff.results) {
    agree(values, "cutoff." + label, result);
  }
  agree(values, "cutoff.limit.count_after_the_thousandth",
        cutoff.count_after_the_thousandth);
  for (const std::string label :
       {"limit.the_thousand_and_first", "launch.refused_once_retired"}) {
    agree(values, "cutoff.receipt." + label, hex(cutoff.receipts.at(label)));
  }
  verify_cap(values, cutoff);
  verify_span(values, span);
}

void verify_invariants(const pv::Values& values, const Harness& cutoff) {
  const auto& population = cutoff.ledger;
  expect_claim(values, "invariants.the_population_satisfies_all",
               v10::conservation_failures(population).empty());

  struct Probe {
    std::string_view name;
    std::string_view failure;
    void (*breaks)(v10::Ledger&);
  };
  const std::array<Probe, 6> probes{{
      {"1_a_key_on_an_unactivated_seat",
       "a machine key names a seat that is not activated",
       [](v10::Ledger& ledger) {
         v10::MachineKey entry;
         entry.machine_public_key = repeated(0x99);
         entry.build_digest = kBuildDigest;
         entry.registered_at_height = 1;
         ledger.machine_keys[200] = entry;
         ledger.machine_key_owners[repeated(0x99)] = 200;
       }},
      {"2_an_owner_entry_missing", "a machine key has no owner entry naming its seat",
       [](v10::Ledger& ledger) { ledger.machine_key_owners.erase(machine_key(0)); }},
      {"3_two_seats_holding_one_key", "two machine-key entries hold the same key",
       [](v10::Ledger& ledger) {
         v10::MachineKey entry;
         entry.machine_public_key = machine_key(0);
         entry.build_digest = kBuildDigest;
         entry.registered_at_height = 1;
         ledger.machine_keys[1] = entry;
       }},
      {"4_a_mark_for_an_unassigned_window",
       "a machine was marked for a window not yet assigned",
       [](v10::Ledger& ledger) {
         ledger.machine_keys.at(0).last_met_window =
             ledger.height / v10::kCycleBlocks - 1;
       }},
      {"5_a_count_for_a_future_window",
       "a machine counted registrations for a future window",
       [](v10::Ledger& ledger) {
         ledger.machine_keys.at(0).registration_window =
             ledger.height / v10::kCycleBlocks + 1;
       }},
      {"6_a_count_above_the_limit",
       "a machine signed more registrations than its limit",
       [](v10::Ledger& ledger) {
         ledger.machine_keys.at(0).registrations_in_window =
             v10::kMachineRegistrationsPerWindow + 1;
       }},
  }};
  for (const auto& probe : probes) {
    auto ledger = population;
    probe.breaks(ledger);
    pv::require(!reports(population, probe.failure),
                "the unbroken population does not report " + std::string(probe.failure));
    expect_claim(values, "invariants." + std::string(probe.name),
                 reports(ledger, probe.failure));
  }

  // The seventh is the block's, because it is about two heights.
  const auto retired = population.launch_retired_at;
  pv::require(retired.has_value(), "the population retired the launch key");
  pv::require(v10::retirement_kept(retired, population),
              "an unchanged retirement is kept");
  auto removed = population;
  removed.launch_retired_at.reset();
  expect_claim(values, "invariants.7_a_retirement_removed",
               !v10::retirement_kept(retired, removed));
  auto moved = population;
  moved.launch_retired_at = *retired + 1;
  expect_claim(values, "invariants.7_a_retirement_moved",
               !v10::retirement_kept(retired, moved));
}

void verify_contract_sections(const pv::Values& contract) {
  // The contract file's genesis is this target's, which the recorded chain
  // identity proves, so what `open_ledger` writes from it is what the vector is
  // about.
  const auto identity = v10::chain_id(trace_genesis());
  pv::require(identity.has_value(), "the trace genesis has a chain identity");
  agree(contract, "genesis.chain_id", hex(*identity));
  const auto entries = v10::economy_entries(open_trace_ledger());
  const bool none = std::none_of(entries.begin(), entries.end(), [](const auto& entry) {
    const auto kind = entry.key.empty() ? 0 : entry.key.front();
    return kind == static_cast<std::uint8_t>(v10::Entry::machine_key) ||
           kind == static_cast<std::uint8_t>(v10::Entry::launch_retirement) ||
           kind == static_cast<std::uint8_t>(v10::Entry::machine_key_owner);
  });
  expect_claim(contract, "genesis.writes_no_registry_entry",
               none && entries.size() == 16);
}

}  // namespace economy_v10_execution

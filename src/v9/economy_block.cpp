// Ordered version-eight block execution: the prologue, the issue step, the
// transactions, the expiry step, then the roots and the header.
//
// `ledger-transition-v1` governs, unchanged: the only valid next height is
// `h + 1`, admission failures are omitted from application execution and from
// the transaction root, every admitted transaction appends a receipt whether it
// succeeds or fails, and the block is atomic in the height and invariant sense
// while ordinary transaction results never reject it.
//
// **Two constructions are inherited rather than re-versioned, and both follow
// from the same clause.** The version-eight specification extends
// `protocol-primitives-v1` and states that definitions there govern unless it
// imposes a narrower rule. It re-versions genesis, the receipt, the state root,
// the chain identity, and the economy tree, and says nothing about the ordered
// transaction tree or the 146-byte application block header, so both stay
// exactly as version one defines them — including the header's schema version
// field of `1`. A version-eight header is already unmistakable without a new
// number, because the chain ID it carries is derived under a version-eight
// label and both state roots it carries are version-eight constructions.
//
// **The block runs at every height, which version seven's does not.** Version
// seven's block does something only if a transaction was offered or a window
// boundary was crossed; version eight audits every in-scope seat at every
// height and resolves those audits `kResponseDeadlineBlocks` later, so a
// transaction-free block still writes state.
//
// **The four steps are ordered and the order is normative:**
//
//   1. the prologue assigns the due window and then deletes its evidence;
//   2. the issue step writes an open challenge for every selected in-scope
//      seat, against the block's `previous_state_root` as its beacon;
//   3. the transactions;
//   4. the expiry step resolves the challenges issued `kResponseDeadlineBlocks`
//      ago, clearing a slot bit for each one nobody answered.
//
// **The assignment is still a prologue.** `uptime-measurement-v1` finalises
// window `w` at the first height of `w + 2`, so that is where `w`'s record is
// written and no earlier — before the block's transactions, so a mint in the
// boundary block can reach the window it just closed.

#include "economy_internal.hpp"
#include "economy_ledger_internal.hpp"

#include "protocol/v1/crypto.hpp"

#include <algorithm>
#include <vector>

#include <array>

namespace protocol::v9 {
namespace {

namespace i = protocol::v9::internal;

constexpr std::array<std::uint8_t, 4> kBlockMagic{'P', 'S', 'B', 'L'};

}  // namespace

Hash transaction_root(std::span<const Hash> admitted_ids) {
  // Version one's ordered transaction tree, duplicates included: a block that
  // offers the same bytes twice commits two leaves, because the tree is over the
  // sequence rather than over a set.
  std::vector<Bytes> leaves;
  leaves.reserve(admitted_ids.size());
  for (const auto& identifier : admitted_ids) {
    leaves.emplace_back(identifier.begin(), identifier.end());
  }
  return i::merkle_root(leaves, kTransactionTreePrefix);
}

std::optional<Bytes> block_header(const Octets32& chain_id, std::uint64_t height,
                                  const Hash& previous_state_root,
                                  const Hash& transaction_root_value,
                                  const Hash& resulting_state_root,
                                  std::uint32_t transaction_count) {
  Bytes raw;
  raw.reserve(kBlockHeaderBytes);
  i::append(raw, std::span<const std::uint8_t>(kBlockMagic));
  i::append_u16(raw, kBlockHeaderSchemaVersion);
  i::append(raw, chain_id);
  i::append_u64(raw, height);
  i::append(raw, previous_state_root);
  i::append(raw, transaction_root_value);
  i::append(raw, resulting_state_root);
  i::append_u32(raw, transaction_count);
  if (raw.size() != kBlockHeaderBytes) return std::nullopt;
  return raw;
}

namespace {

// The six ordered steps at an assignment height.
//
// **The figures are accumulated from the same sequence the settlement derived**,
// in the same prologue, so version nine adds no second walk over the seat table
// at a window boundary: step 5 reads what step 1 already produced. That is also
// why the accumulation-before-deletion order is unobservable here — the sequence
// is derived once, before either step, so the deletion cannot take anything the
// accumulation still needs. ADR 0078 records the equality with its reason, and
// `delete_before_accumulate` is what lets a trace demonstrate it.
bool assign_due_window(Ledger& ledger, BlockOutcome& outcome, std::uint64_t due,
                       const BlockOrder& order) {
  // The month the closing settlement needs, read from the entry written at the
  // window's own opening height. A window assigned with no recorded month is a
  // state no conforming chain reaches.
  const auto recorded = ledger.window_months.find(due);
  if (recorded == ledger.window_months.end()) return false;
  const auto due_month = recorded->second;
  outcome.due_month = due_month;

  // Step 1, and steps 1 through 7 of version seven's settlement, which
  // `apply_assignment` performs together.
  const auto measured = derive_schedule(ledger, due);
  std::optional<Assignment> assignment;
  if (!measured.empty()) {
    assignment = derive_assignment(ledger, due, measured);
    if (!assignment) return false;
  }

  const auto settle = [&]() -> bool {
    // `due - 1` is the last window attributed to the closing month, because the
    // cursor was set to that month at its assignment.
    const auto closed = close_month(ledger, due_month, due - 1);
    if (!closed) return false;
    ledger.accumulating_month = due_month;
    outcome.settled = closed->settled;
    outcome.skipped_months = closed->skipped;
    return true;
  };
  const auto accrue = [&]() -> bool {
    if (!assignment) return true;
    if (!apply_assignment(ledger, *assignment)) return false;
    outcome.assigned_window = due;
    outcome.assignment = *assignment;
    return true;
  };

  // Steps 3 then 4. **The payout precedes the accrual** because the window being
  // assigned belongs to the new month, so its referral accrual is the new
  // month's: letting it land first would pay the closing month one window of its
  // successor's accrual, every month, by a day.
  if (order.settle_before_accrual) {
    if (!settle() || !accrue()) return false;
  } else {
    if (!accrue() || !settle()) return false;
  }

  // Step 5. Only nonzero figures are written: a candidate with no entry has a
  // figure of zero by absence, which is the difference between writing as many
  // entries as ran and writing 100,000 every window.
  const auto accumulate = [&]() -> bool {
    for (const auto& seat : measured) {
      if (seat.uptime_seconds == 0) continue;
      auto& figure = ledger.figures[{due_month, seat.seat_id}];
      if (seat.uptime_seconds > kMaxU64 - figure) return false;
      figure += seat.uptime_seconds;
    }
    return true;
  };
  // Step 6. The kind-19 entries for the due window and its kind-20 entry.
  // Version eight deletes the records immediately after the assignment; version
  // nine moves the deletion to the end of the prologue and changes nothing else
  // about it.
  const auto discard = [&]() {
    auto key = i::key_prefix(Entry::seat_window);
    i::append_u64(key, due);
    for (auto entry = ledger.uptime.lower_bound(key);
         entry != ledger.uptime.end();) {
      if (entry->first.size() < key.size() ||
          !std::equal(key.begin(), key.end(), entry->first.begin())) {
        break;
      }
      entry = ledger.uptime.erase(entry);
    }
    ledger.window_months.erase(due);
  };

  if (order.delete_before_accumulate) {
    discard();
    return accumulate();
  }
  if (!accumulate()) return false;
  discard();
  return true;
}

// Step 1. Assign window `h / kCycleBlocks - 2` from state, then delete its
// evidence.
//
// **Nothing is supplied.** The measured seats are derived from the seat table
// and the window records, so record completeness is structural: a seat cannot be
// omitted, and a seat with no record is present with a full credit rather than
// absent. A window with no in-scope seats writes nothing, which is the same fact
// as a record with every bit clear.
//
// **The deletion runs whether or not an assignment was written**, because a
// window with no in-scope seats has no records either and deleting nothing is
// the same fact. Running it unconditionally is what makes invariant 5 — exactly
// two windows retained at every height, including a boundary height — hold
// without a second rule about which boundary heights delete.
//
// `false` is a whole-block rejection rather than an absent assignment.
bool prologue(Ledger& ledger, BlockOutcome& outcome, const BlockOrder& order) {
  if (ledger.height % kCycleBlocks != 0) return true;
  const auto window = ledger.height / kCycleBlocks;
  if (window >= kAssignmentLagWindows &&
      !assign_due_window(ledger, outcome, window - kAssignmentLagWindows, order)) {
    return false;
  }

  // **At every window-opening height, including those below the assignment
  // lag.** A window's month is fixed by the timestamp of its first height, and
  // that height is 57,600 blocks behind the block that assigns it and therefore
  // not reachable from it. Reading the month from the assigning block instead is
  // the systematic two-day distortion `unreferred-pool-payout-v1` rejects by
  // name.
  //
  // An entry that already exists for this window is an invariant failure,
  // because a window opens once.
  if (ledger.window_months.contains(window)) return false;
  const auto month = month_index(ledger.timestamp);
  if (!month) return false;
  ledger.window_months.emplace(window, *month);
  outcome.opened_window = window;
  return true;
}

// Step 2. One open challenge per selected in-scope seat, in ascending seat
// order.
//
// The beacon is the block's own `previous_state_root`, which is already
// computed, read once at the height it belongs to, and never stored. A retained
// ring of past roots would be new consensus state whose only purpose is to
// re-derive something already derived.
//
// This is the pipeline's whole consensus-visible cost: one digest per in-scope
// seat per challengeable height. The evaluation is order-independent and may be
// parallelised; the entries it writes are in ascending seat order.
bool issue_step(Ledger& ledger, const Hash& beacon, BlockOutcome& outcome) {
  const auto window = window_of_height(ledger.height);
  for (const auto& [seat_id, seat] : ledger.seats) {
    if (!seat.is_activated) continue;
    if (!seat_in_scope(seat.activation_height, window)) continue;
    const auto selected = is_selected(beacon, seat_id, ledger.height);
    if (!selected) return false;
    if (!*selected) continue;
    if (!i::issue_challenge(ledger, ledger.height, seat_id)) return false;
    outcome.issued.push_back(seat_id);
  }
  return true;
}

// Step 4. Resolve and delete every challenge issued `kResponseDeadlineBlocks`
// ago.
//
// An answered challenge is deleted and nothing else is written; an outstanding
// one clears the seat's bit for the slot of its *challenge* height, which is the
// accepted model's slot-close sweep made incremental and exact.
bool expiry_step(Ledger& ledger, BlockOutcome& outcome) {
  if (ledger.height <= kResponseDeadlineBlocks) return true;
  const auto due = ledger.height - kResponseDeadlineBlocks;

  auto prefix = i::key_prefix(Entry::open_challenge);
  i::append_u64(prefix, due);
  std::vector<ChallengeRef> pending;
  for (auto entry = ledger.uptime.lower_bound(prefix);
       entry != ledger.uptime.end(); ++entry) {
    if (entry->first.size() < prefix.size() ||
        !std::equal(prefix.begin(), prefix.end(), entry->first.begin())) {
      break;
    }
    const auto seat = i::read_u32(entry->first, prefix.size());
    if (!seat) return false;
    pending.push_back(ChallengeRef{due, *seat});
  }
  // Collected before any is resolved, because resolving one erases its entry
  // and invalidates an iterator walking the same map.
  for (const auto& challenge : pending) {
    bool lost = false;
    if (!i::expire_challenge(ledger, challenge.challenge_height,
                             challenge.seat_id, lost)) {
      return false;
    }
    outcome.expired.push_back(challenge);
    if (lost) outcome.lost_slots.push_back(challenge);
  }
  return true;
}

}  // namespace

std::optional<BlockOutcome> execute_block(Ledger& ledger, std::uint64_t timestamp,
                                          std::span<const Bytes> raw_inputs,
                                          const SignatureVerifier& verify,
                                          const BlockOrder& order) {
  if (raw_inputs.size() > kMaxRawInputs) return std::nullopt;
  const auto previous_root = ledger_state_root(ledger);
  if (!previous_root || ledger.height == kMaxU64) return std::nullopt;

  // **Step 0, and it runs before anything reads the field.** That is what keeps
  // every derivation total: a value outside the accepted range has no month, and
  // no step should ever be handed one. `replay_timestamp` is what is called
  // here and it takes no clock, so C5 is not reachable from this path — a
  // machine that re-applied the tolerance while replaying history would reject
  // the chain's own past one tolerance-width after producing it, and the failure
  // would be silent.
  if (replay_timestamp({ledger.height, ledger.timestamp}, ledger.height + 1,
                       timestamp) != TimestampCondition::accepted) {
    return std::nullopt;
  }

  // The block transition is atomic: an internal invariant failure, height error,
  // timestamp error, or resource-bound violation rejects the whole proposed
  // block and preserves the pre-block state. Ordinary transaction results never
  // reach here, because a refusal is a result rather than a failure.
  const Ledger snapshot = ledger;
  BlockOutcome outcome;
  outcome.height = ledger.height + 1;
  outcome.timestamp = timestamp;
  outcome.previous_state_root = *previous_root;
  ledger.height = outcome.height;
  ledger.timestamp = timestamp;

  // Steps 1 and 2, in the normative order. At the accepted lag of two windows
  // the two provably cannot touch the same entry, so `issue_before_prologue`
  // commits the same root; the flag exists so a trace can demonstrate that
  // rather than assert it.
  const bool ok = order.issue_before_prologue
                      ? issue_step(ledger, outcome.previous_state_root, outcome) &&
                            (!order.assignment_is_prologue ||
                             prologue(ledger, outcome, order))
                      : (!order.assignment_is_prologue ||
                         prologue(ledger, outcome, order)) &&
                            issue_step(ledger, outcome.previous_state_root,
                                       outcome);
  if (!ok) {
    ledger = snapshot;
    return std::nullopt;
  }

  // Step 4 runs after the transactions, and that ordering is observable: a
  // response arriving in block `c + kResponseDeadlineBlocks` is counted, and
  // expiring first would discard the last admissible response to every
  // challenge and shorten the deadline to nineteen blocks without saying so.
  if (order.expire_before_transactions && !expiry_step(ledger, outcome)) {
    ledger = snapshot;
    return std::nullopt;
  }

  std::vector<Hash> admitted_ids;
  for (const auto& raw : raw_inputs) {
    auto admission = admit(raw, ledger.chain_id, verify);
    if (!admission.admitted()) {
      outcome.admissions.push_back(std::move(admission));
      continue;
    }
    const auto before = ledger_state_root(ledger);
    const auto result = execute(ledger, admission.transaction.envelope, verify);
    if (!before || !result) {
      ledger = snapshot;
      return std::nullopt;
    }
    if (!result->succeeded()) {
      // Failed-transition atomicity, checked rather than asserted: a refusal
      // writes nothing, so the commitment over the whole state must be the value
      // it was before the transaction was offered.
      const auto after = ledger_state_root(ledger);
      if (!after || *after != *before) {
        ledger = snapshot;
        return std::nullopt;
      }
      outcome.atomic_failures += 1;
    }
    ExecutedTransaction executed;
    executed.transaction_id = admission.transaction_id;
    executed.kind = admission.transaction.envelope.kind;
    executed.outcome = *result;
    executed.receipt = receipt_for(admission.transaction_id,
                                   admission.transaction.envelope, *result);
    admitted_ids.push_back(admission.transaction_id);
    outcome.executed.push_back(std::move(executed));
    outcome.admissions.push_back(std::move(admission));
  }
  if (outcome.executed.size() > kMaxAdmitted) {
    ledger = snapshot;
    return std::nullopt;
  }

  if (!order.assignment_is_prologue && !prologue(ledger, outcome, order)) {
    ledger = snapshot;
    return std::nullopt;
  }
  if (!order.expire_before_transactions && !expiry_step(ledger, outcome)) {
    ledger = snapshot;
    return std::nullopt;
  }

  if (!conservation_failures(ledger).empty()) {
    ledger = snapshot;
    return std::nullopt;
  }
  const auto resulting_root = ledger_state_root(ledger);
  if (!resulting_root) {
    ledger = snapshot;
    return std::nullopt;
  }
  outcome.resulting_state_root = *resulting_root;
  outcome.transaction_root = transaction_root(admitted_ids);
  const auto header = block_header(
      ledger.chain_id, outcome.height, outcome.timestamp,
      outcome.previous_state_root, outcome.transaction_root,
      outcome.resulting_state_root,
      static_cast<std::uint32_t>(outcome.executed.size()));
  if (!header) {
    ledger = snapshot;
    return std::nullopt;
  }
  const auto identifier = block_id(*header);
  if (!identifier) {
    ledger = snapshot;
    return std::nullopt;
  }
  outcome.header = *header;
  outcome.block_id = *identifier;
  return outcome;
}

namespace {

std::optional<StateRootFrame> frame_of(const Ledger& ledger) {
  StateSummary summary;
  summary.chain_id = ledger.chain_id;
  summary.height = ledger.height;
  summary.timestamp = ledger.timestamp;
  summary.supply_limit = ledger.supply_limit;
  summary.total_supply = ledger.total_supply;
  summary.fee_pool_balance = ledger.fee_pool;
  return state_root_frame(summary, account_entries(ledger),
                          economy_entries(ledger));
}

}  // namespace

std::optional<QuietRun> run_quiet_heights(Ledger& ledger,
                                          std::uint64_t target_height,
                                          const TimestampOfHeight& timestamp_of,
                                          const SignatureVerifier& verify,
                                          const Responder& respond) {
  if (target_height < ledger.height || !timestamp_of) return std::nullopt;
  QuietRun run;
  auto frame = frame_of(ledger);
  if (!frame) return std::nullopt;
  std::vector<Bytes> pending;

  while (ledger.height < target_height) {
    const auto height = ledger.height + 1;
    const auto timestamp = timestamp_of(height);
    std::vector<std::uint32_t> issued;
    // A height that opens a window or that has an input offered runs the whole
    // block transition, so the prologue, the conservation gate, and the header
    // are never skipped.
    if (!pending.empty() || height % kCycleBlocks == 0) {
      auto block = execute_block(ledger, timestamp, pending, verify);
      if (!block) return std::nullopt;
      issued = block->issued;
      run.recorded.push_back(std::move(*block));
      frame = frame_of(ledger);
      if (!frame) return std::nullopt;
    } else {
      // **The quiet path applies C1 and C2 too.** A fast path that advanced the
      // height and left the stamp behind would commit a root naming a height the
      // stamp does not belong to, and every later block would still satisfy C2
      // because the stale stamp is smaller — a wrong root rather than a refusal,
      // which is the direction that hides.
      if (replay_timestamp({ledger.height, ledger.timestamp}, height, timestamp) !=
          TimestampCondition::accepted) {
        return std::nullopt;
      }
      const auto beacon =
          state_root_from_frame(*frame, ledger.height, ledger.timestamp);
      if (!beacon) return std::nullopt;
      ledger.height = height;
      ledger.timestamp = timestamp;
      BlockOutcome quiet;
      if (!issue_step(ledger, *beacon, quiet)) return std::nullopt;
      if (!expiry_step(ledger, quiet)) return std::nullopt;
      // The six uptime invariants at every height, because the two steps that
      // just ran are the only ones that can break them and a quiet height runs
      // no other gate. The full conservation walk runs at every *recorded*
      // block, which is where a transaction could have moved value.
      if (!i::uptime_failures(ledger).empty()) return std::nullopt;
      issued = quiet.issued;
      if (!quiet.issued.empty() || !quiet.expired.empty()) {
        frame = frame_of(ledger);
        if (!frame) return std::nullopt;
      }
    }
    pending = respond ? respond(height, issued) : std::vector<Bytes>{};
    run.heights += 1;
  }
  // A responder that produced an input for a height past the target would have
  // it silently dropped, so the run refuses instead.
  if (!pending.empty()) return std::nullopt;
  return run;
}

}  // namespace protocol::v9

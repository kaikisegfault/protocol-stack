// Ordered version-seven block execution: the prologue, the transactions, the
// roots, the header.
//
// `ledger-transition-v1` governs, unchanged: the only valid next height is
// `h + 1`, admission failures are omitted from application execution and from
// the transaction root, every admitted transaction appends a receipt whether it
// succeeds or fails, and the block is atomic in the height and invariant sense
// while ordinary transaction results never reject it.
//
// **Two constructions are inherited rather than re-versioned, and both follow
// from the same clause.** The version-seven specification extends
// `protocol-primitives-v1` and states that definitions there govern unless it
// imposes a narrower rule. It re-versions genesis, the receipt, and the state
// root explicitly and says nothing about the ordered transaction tree or the
// 146-byte application block header, so both stay exactly as version one defines
// them — including the header's schema version field of `1`. A version-seven
// header is already unmistakable without a new number, because the chain ID it
// carries is derived under a version-seven label and both state roots it carries
// are version-seven constructions.
//
// **The assignment is a prologue.** `uptime-measurement-v1` finalises window `w`
// at the first height of `w + 2`, so that is where `w`'s record is written and
// no earlier — before the block's transactions, so a mint in the boundary block
// can reach the window it just closed.

#include "economy_internal.hpp"
#include "economy_ledger_internal.hpp"

#include "protocol/v1/crypto.hpp"

#include <array>

namespace protocol::v7 {
namespace {

namespace i = protocol::v7::internal;

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

// Write window `h / kCycleBlocks - 2`'s record when `h` opens a window.
//
// A window with no finalised measurement — a chain with no seats in scope —
// writes nothing, which is the same fact as a record with every bit clear.
// `false` is a whole-block rejection rather than an absent assignment.
bool write_due_assignment(Ledger& ledger, const UptimeSchedule* uptime,
                          std::optional<std::uint64_t>& assigned) {
  if (ledger.height % kCycleBlocks != 0) return true;
  const auto window = ledger.height / kCycleBlocks;
  if (window < kAssignmentLagWindows) return true;
  const auto due = window - kAssignmentLagWindows;
  if (uptime == nullptr) return true;
  const auto measured = uptime->find(due);
  if (measured == uptime->end() || measured->second.empty()) return true;

  const auto assignment = derive_assignment(ledger, due, measured->second);
  if (!assignment) return false;
  if (!apply_assignment(ledger, *assignment)) return false;
  assigned = due;
  return true;
}

}  // namespace

std::optional<BlockOutcome> execute_block(Ledger& ledger,
                                          std::span<const Bytes> raw_inputs,
                                          const SignatureVerifier& verify,
                                          const UptimeSchedule* uptime,
                                          bool assignment_is_prologue) {
  if (raw_inputs.size() > kMaxRawInputs) return std::nullopt;
  const auto previous_root = ledger_state_root(ledger);
  if (!previous_root || ledger.height == kMaxU64) return std::nullopt;

  // The block transition is atomic: an internal invariant failure, height error,
  // or resource-bound violation rejects the whole proposed block and preserves
  // the pre-block state. Ordinary transaction results never reach here, because
  // a refusal is a result rather than a failure.
  const Ledger snapshot = ledger;
  BlockOutcome outcome;
  outcome.height = ledger.height + 1;
  outcome.previous_state_root = *previous_root;
  ledger.height = outcome.height;

  if (assignment_is_prologue &&
      !write_due_assignment(ledger, uptime, outcome.assigned_window)) {
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

  if (!assignment_is_prologue &&
      !write_due_assignment(ledger, uptime, outcome.assigned_window)) {
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
  const auto header = block_header(
      ledger.chain_id, outcome.height, outcome.previous_state_root,
      transaction_root(admitted_ids), outcome.resulting_state_root,
      static_cast<std::uint32_t>(outcome.executed.size()));
  if (!header) {
    ledger = snapshot;
    return std::nullopt;
  }
  outcome.header = *header;
  outcome.block_id = protocol::v1::hash(kBlockIdLabel, outcome.header);
  return outcome;
}

}  // namespace protocol::v7

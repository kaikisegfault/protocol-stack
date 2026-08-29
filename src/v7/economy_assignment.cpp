// The cycle assignment: deriving one window's outcome and writing it.
//
// Steps 1 through 4 are version three's, unchanged. Steps 5 through 7 are
// version seven's, and they are what ADR 0049 directs:
//
// 5. every contributing seat adds a whole base permission to `outstanding`, with
//    nothing moved out;
// 6. a cycle with any winner absorbs 100% of the recovery pool **as it stood
//    before this cycle**;
// 7. each leg is divided among the winners, and both remainders — the
//    reallocation dust and the residual of the pool just divided — become the
//    pool for the cycle after.
//
// **Step 6 reads before step 7 writes**, so a cycle never pays itself its own
// dust. That order is the difference between two self-consistent readings of ADR
// 0049's sentence, which is why the specification states it and this file
// performs it in exactly that order rather than in a convenient one.
//
// **Two seat sets are named and neither may be narrowed to the other.** The
// *contributing* set is the in-span seats, which generate permissions. The
// *eligible* set is every measured seat that met the cycle and is under the
// accumulation cap, **in span or not**, and it is the candidate set the winner
// derivation ranks. A winner derivation filtered by span would strand the pool
// the moment the last in-span machine finished, and the failure would be silent
// because every identity would still hold.

#include "economy_ledger_internal.hpp"

#include <algorithm>

namespace protocol::v7 {
namespace {

// The founder-directed activity threshold: 18 hours of cumulative fully
// operational uptime per cycle, read from the accepted manifest layer and
// checked by the kernel tests against `test-vectors/economy-transition-v3.txt`.
constexpr std::uint64_t kActivityThresholdSeconds = 64'800;

bool met_cycle(std::uint64_t uptime_seconds) {
  return uptime_seconds >= kActivityThresholdSeconds;
}

// The seats at the highest uptime among those eligible to receive. The candidate
// set is restricted *before* the maximum is taken: taking the maximum first and
// filtering afterwards would return an empty set whenever the best uptime in a
// cycle belonged to a seat that failed it or that had stopped collecting, and
// neither rewards anyone.
// `eligible` is `std::vector<bool>` by reference rather than a span, because the
// standard's bit-packed specialisation has no contiguous `bool` to span over.
std::vector<std::uint32_t> derive_winner_set(
    std::span<const SeatCycle> measured, const std::vector<bool>& eligible) {
  std::uint64_t best = 0;
  bool any = false;
  for (std::size_t index = 0; index < measured.size(); ++index) {
    if (!eligible[index]) continue;
    if (!any || measured[index].uptime_seconds > best) {
      best = measured[index].uptime_seconds;
      any = true;
    }
  }
  std::vector<std::uint32_t> winners;
  if (!any) return winners;
  for (std::size_t index = 0; index < measured.size(); ++index) {
    if (eligible[index] && measured[index].uptime_seconds == best) {
      winners.push_back(measured[index].seat_id);
    }
  }
  std::sort(winners.begin(), winners.end());
  return winners;
}

}  // namespace

std::optional<Assignment> derive_assignment(const Ledger& ledger,
                                            std::uint64_t cycle_window,
                                            std::span<const SeatCycle> measured) {
  Assignment assignment;
  assignment.cycle_window = cycle_window;
  assignment.in_scope_count = static_cast<std::uint32_t>(measured.size());
  assignment.pool_before = ledger.pool;

  // **The mark and the recorded referrer are read from the seat entry**, never
  // from the measurement. ADR 0055 derives this from two sentences of the
  // accepted settlement: step 3 filters on the accumulation cap, which is
  // defined against `minted_through_window`, and step 7 accrues to "the seat's
  // *recorded* referrer identity". Both name state, and only the seat entry
  // holds it. A measurement able to supply a different mark could set an accrued
  // bit in a window the seat's own mint can no longer reach, which is exactly
  // the stranding the backing identity exists to make impossible.
  std::vector<bool> eligible(measured.size(), false);
  std::vector<const SeatRecord*> entries(measured.size(), nullptr);
  std::vector<std::uint32_t> seen;
  seen.reserve(measured.size());
  for (std::size_t index = 0; index < measured.size(); ++index) {
    const auto& seat = measured[index];
    // A measurement naming a seat no transaction ever purchased describes a
    // machine the chain does not know, and there is no seat entry to read. It
    // rejects the whole block rather than assigning against an invented zero.
    const auto entry = ledger.seats.find(seat.seat_id);
    if (entry == ledger.seats.end()) return std::nullopt;
    if (std::find(seen.begin(), seen.end(), seat.seat_id) != seen.end()) {
      return std::nullopt;
    }
    seen.push_back(seat.seat_id);
    entries[index] = &entry->second;
    eligible[index] = met_cycle(seat.uptime_seconds) &&
                      accrues(cycle_window, entry->second.minted_through_window);
    if (seat.seat_id >= assignment.bitmap_bits) {
      assignment.bitmap_bits = seat.seat_id + 1;
    }
  }

  // Step 3. Every measured seat is a candidate, in span or not.
  for (const auto flag : eligible) {
    if (flag) ++assignment.eligible_count;
  }
  assignment.winners = derive_winner_set(measured, eligible);
  const auto winner_count = static_cast<std::uint32_t>(assignment.winners.size());

  // Step 4. The contributing set is the in-span seats, and only they accrue.
  std::uint32_t contributing = 0;
  for (std::size_t index = 0; index < measured.size(); ++index) {
    if (!measured[index].in_span) continue;
    ++contributing;
    if (eligible[index]) assignment.accrued.push_back(measured[index].seat_id);
  }
  std::sort(assignment.accrued.begin(), assignment.accrued.end());
  assignment.contributing_count = contributing;
  assignment.reallocated_count =
      contributing - static_cast<std::uint32_t>(assignment.accrued.size());

  // Step 6. Absorb before dividing, so this cycle's own dust belongs to the next
  // one. A cycle with no winner absorbs nothing and leaves the pool untouched.
  if (winner_count != 0) assignment.pool_absorbed = assignment.pool_before;

  // Step 7. Divide both, and return both remainders to the pool.
  const auto split = split_permission(winner_count);
  assignment.share_per_winner_atomic = split.share[kFounderOperatorChannel];
  for (std::size_t channel = 0; channel < kRecoveryPoolLegs; ++channel) {
    const auto taken = assignment.pool_absorbed[channel];
    const auto pool_share = winner_count == 0 ? 0 : taken / winner_count;
    const auto pool_residual = taken - pool_share * winner_count;
    std::uint64_t dust = 0;
    if (split.remainder[channel] != 0 &&
        assignment.reallocated_count > kMaxU64 / split.remainder[channel]) {
      return std::nullopt;
    }
    dust = split.remainder[channel] * assignment.reallocated_count;
    const auto before = assignment.pool_before[channel];
    if (taken > before) return std::nullopt;
    std::uint64_t after = before - taken;
    if (pool_residual > kMaxU64 - after) return std::nullopt;
    after += pool_residual;
    if (dust > kMaxU64 - after) return std::nullopt;
    after += dust;
    assignment.pool_after[channel] = after;
  }

  // Step 8, which is version three's step 7 unchanged: accrue the referral leg
  // for each contributing seat, to the seat's recorded referrer identity when it
  // has one and that identity is under the cap, and to the unreferred pool
  // otherwise. A referrer over the cap forfeits, and the forfeited value stays
  // inside the `founder_referral` channel.
  for (std::size_t index = 0; index < measured.size(); ++index) {
    if (!measured[index].in_span) continue;
    const auto& entry = *entries[index];
    if (!entry.has_referrer) {
      if (kReferralLegAtomic > kMaxU64 - assignment.unreferred_accrual) {
        return std::nullopt;
      }
      assignment.unreferred_accrual += kReferralLegAtomic;
      continue;
    }
    const auto balance = ledger.referral.find(entry.referrer_hub_identity);
    if (balance != ledger.referral.end() &&
        !accrues(cycle_window, balance->second.collected_through_window)) {
      if (kReferralLegAtomic > kMaxU64 - assignment.unreferred_accrual) {
        return std::nullopt;
      }
      assignment.unreferred_accrual += kReferralLegAtomic;
      continue;
    }
    auto& accrual = assignment.referral_accruals[entry.referrer_hub_identity];
    if (kReferralLegAtomic > kMaxU64 - accrual) return std::nullopt;
    accrual += kReferralLegAtomic;
  }
  return assignment;
}

std::optional<Bytes> assignment_value(const Assignment& assignment) {
  CycleAssignment record;
  record.share_per_winner_atomic = assignment.share_per_winner_atomic;
  record.reallocated_count = assignment.reallocated_count;
  record.winner_count = static_cast<std::uint32_t>(assignment.winners.size());
  record.in_scope_count = assignment.in_scope_count;
  record.bitmap_bits = assignment.bitmap_bits;
  record.pool_absorbed = assignment.pool_absorbed;
  const auto accrued = bitmap(assignment.accrued, assignment.bitmap_bits);
  const auto winners = bitmap(assignment.winners, assignment.bitmap_bits);
  if (!accrued || !winners) return std::nullopt;
  record.accrued_bitmap = *accrued;
  record.winner_bitmap = *winners;
  return cycle_assignment_value(record);
}

bool apply_assignment(Ledger& ledger, const Assignment& assignment) {
  if (ledger.assignments.contains(assignment.cycle_window)) return false;
  const auto value = assignment_value(assignment);
  if (!value) return false;
  ledger.assignments[assignment.cycle_window] = *value;

  // Step 5. The whole base permission per contributing seat enters
  // `outstanding`, with nothing moved out. Version six subtracted the carried
  // remainder here; leaving it in and naming the unclaimable part with the pool
  // entry instead is what removes the identity's third term.
  for (std::uint8_t channel = 0; channel < kRecoveryPoolLegs; ++channel) {
    const auto leg = base_permission_leg(channel);
    if (leg != 0 && assignment.contributing_count > kMaxU64 / leg) return false;
    const auto delta = leg * assignment.contributing_count;
    if (delta > kMaxU64 - ledger.channel_outstanding[channel]) return false;
    ledger.channel_outstanding[channel] += delta;
  }
  ledger.pool = assignment.pool_after;

  for (const auto& [identity, amount] : assignment.referral_accruals) {
    auto& balance = ledger.referral[identity];
    if (amount > kMaxU64 - balance.accrued_atomic) return false;
    balance.accrued_atomic += amount;
    if (amount > kMaxU64 - ledger.channel_outstanding[kReferralChannel]) return false;
    ledger.channel_outstanding[kReferralChannel] += amount;
  }
  if (assignment.unreferred_accrual > kMaxU64 - ledger.pool_accrued) return false;
  ledger.pool_accrued += assignment.unreferred_accrual;
  if (assignment.unreferred_accrual >
      kMaxU64 - ledger.channel_outstanding[kReferralChannel]) {
    return false;
  }
  ledger.channel_outstanding[kReferralChannel] += assignment.unreferred_accrual;

  if (assignment.contributing_count > kMaxU64 - ledger.assigned_permissions) {
    return false;
  }
  ledger.assigned_permissions += assignment.contributing_count;
  return true;
}

}  // namespace protocol::v7

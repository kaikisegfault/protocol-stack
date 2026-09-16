// The monthly settlement: which month closes, who competes, and what is paid.
//
// **Everything version nine adds to execution is here except kind 22**, which
// lives beside kind 4 because it *is* kind 4 with a different balance, and the
// two prologue steps, which are two calls inside the block. So the difference
// between version eight's execution and version nine's is this file, one arm in
// `economy_value_transitions.cpp`, and a handful of lines in
// `economy_block.cpp` — the shape `economy_uptime.cpp` established for version
// eight's codec, applied to a version's execution.
//
// This is `unreferred-pool-payout-v1`'s rule over the quantities version nine
// encodes, and every function below is **pure** except `close_month`: they read
// no ledger and write none, so the arithmetic is exercisable against the
// recorded contract vectors without a chain, and the prologue is the only thing
// that applies it.
//
// **Exactly one month can close per assignment, and that is a rule rather than
// an optimisation.** Window attribution is non-decreasing and consecutive
// assigned windows carry the cursor's month and the new one with nothing between
// them, so every index strictly between is an empty month: no window is
// attributed to it, so it has no accrual and no candidates, and a pass over it
// leaves the balance exactly as it found it. The gap is bounded by nothing a
// chain controls — a network halted for a year resumes with twelve empty months
// between — so iterating it would make one block's work proportional to how long
// the network was down.
//
// **No invariant over a single accepted state separates the single pass from the
// loop**, because they agree on every state both produce. What separates them is
// a scenario, which is why the vectors settle a multi-month halt both ways.

#include "economy_ledger_internal.hpp"

#include <algorithm>
#include <utility>

namespace protocol::v9 {
namespace {

// The seat set the ranking is taken over. Ascending by construction, because a
// `std::map` keyed by seat identifier is.
std::uint64_t figure_of(const std::map<std::uint32_t, std::uint64_t>& figures,
                        std::uint32_t seat_id) {
  const auto found = figures.find(seat_id);
  return found == figures.end() ? 0 : found->second;
}

}  // namespace

std::vector<std::string_view> pool_failures(
    const Pool& pool, const std::map<std::uint32_t, MonthlyClaim>& claims) {
  std::vector<std::string_view> failures;
  std::uint64_t assigned = 0;
  std::uint64_t taken = 0;
  for (const auto& [seat_id, claim] : claims) {
    (void)seat_id;
    if (claim.accrued_atomic > kMaxU64 - assigned) {
      failures.push_back("the claims' accrued total leaves u64");
      return failures;
    }
    assigned += claim.accrued_atomic;
    if (claim.minted_atomic > kMaxU64 - taken) {
      failures.push_back("the claims' minted total leaves u64");
      return failures;
    }
    taken += claim.minted_atomic;
  }
  // Every unit the pool has received is either still undistributed or is owed to
  // a named winner, and none is anywhere else.
  if (pool.payable_atomic > kMaxU64 - assigned ||
      pool.accrued_atomic != pool.payable_atomic + assigned) {
    failures.push_back("the pool's accrued is not its payable plus what it assigned");
  }
  // **An equality rather than the bound `minted <= accrued - payable`**, because
  // an equality catches a unit minted twice and the bound does not.
  if (pool.minted_atomic != taken) {
    failures.push_back("the pool's minted is not the claims' minted total");
  }
  return failures;
}

std::vector<std::uint32_t> settlement_candidates(const Ledger& ledger,
                                                 std::uint64_t last_window) {
  std::vector<std::uint32_t> candidates;
  for (const auto& [seat_id, seat] : ledger.seats) {
    if (!seat.is_activated) continue;
    if (first_cycle_window(seat.activation_height) <= last_window) {
      candidates.push_back(seat_id);
    }
  }
  return candidates;
}

std::optional<Settlement> settle_month(
    std::uint32_t month, std::span<const std::uint32_t> candidates,
    const std::map<std::uint32_t, std::uint64_t>& figures, std::uint64_t payable) {
  Settlement settlement;
  settlement.month = month;
  settlement.payable_before = payable;

  if (candidates.empty()) {
    // The theorem `unreferred-pool-payout-v1` proves: an accrual in a month
    // implies a seat was in span in a window attributed to it, in-span implies
    // in-scope by construction, and in-scope never expires. **A month that
    // accumulated uptime and has nobody to pay means the derivation is broken,
    // not that the carry is doing its job**, so it is a whole-block rejection
    // rather than a carried month. It is checked on every settlement rather than
    // asserted once, so a later change that made in-scope expire fails a test
    // instead of quietly turning a safety net into a policy.
    if (!figures.empty()) return std::nullopt;
    settlement.remainder = payable;
    return settlement;
  }

  settlement.candidate_count = static_cast<std::uint32_t>(candidates.size());
  for (const auto seat_id : candidates) {
    settlement.best_figure =
        std::max(settlement.best_figure, figure_of(figures, seat_id));
  }
  // **`best` may be zero, and then every candidate wins.** ADR 0075 declined a
  // duty gate and ADR 0076 declined an accumulation-cap filter, so a month in
  // which no in-scope seat was credited for a single slot splits the balance
  // across every in-scope seat. It is reachable, it is not an error, and it is
  // not to be filtered.
  for (const auto seat_id : candidates) {
    if (figure_of(figures, seat_id) == settlement.best_figure) {
      settlement.winners.push_back(seat_id);
    }
  }
  const auto winner_count = static_cast<std::uint64_t>(settlement.winners.size());
  settlement.share = payable / winner_count;
  settlement.assigned = settlement.share * winner_count;
  settlement.remainder = payable - settlement.assigned;
  return settlement;
}

namespace {

// Write what a settlement decided: the claims, the balance, the deletion.
//
// **A zero share writes no claim entry**, which is a rule rather than an
// optimisation: a claim is a balance and a balance of zero is absence, the same
// rule the monthly figure follows and the same rule `protocol-primitives-v1`
// imposes everywhere. In the zero-best month that is the difference between
// writing up to 100,000 entries recording that nobody was paid anything and
// writing none.
bool apply_settlement(Ledger& ledger, const Settlement& settlement) {
  if (settlement.share != 0) {
    for (const auto seat_id : settlement.winners) {
      auto& claim = ledger.claims[seat_id];
      if (settlement.share > kMaxU64 - claim.accrued_atomic) return false;
      claim.accrued_atomic += settlement.share;
    }
  }
  ledger.pool_payable = settlement.remainder;
  // The largest state change this rule makes: up to 100,000 entries in one
  // block at capacity, though only for seats that actually ran.
  std::erase_if(ledger.figures, [&settlement](const auto& entry) {
    return entry.first.first == settlement.month;
  });
  return true;
}

}  // namespace

std::optional<ClosedMonth> close_month(Ledger& ledger, std::uint32_t due_month,
                                       std::uint64_t last_window) {
  // **A due month behind the cursor is an invariant failure.**
  // `month_of_window` is non-decreasing in the window index, because
  // `month_index` is non-decreasing in the timestamp, C2 makes the timestamp
  // non-decreasing in the height, and window opening heights increase. A chain
  // that reached this state has a corrupted cursor or a corrupted month entry,
  // and there is no correct way to continue from it.
  if (due_month < ledger.accumulating_month) return std::nullopt;
  if (due_month > kMaxMonthIndex || ledger.accumulating_month > kMaxMonthIndex) {
    return std::nullopt;
  }

  ClosedMonth closed;
  // **When the months are equal, nothing closes.** The assigned window belongs
  // to the month already accumulating, its figures join that month's, and
  // `payable` is untouched. This is every assignment but roughly one a month.
  if (due_month == ledger.accumulating_month) return closed;

  const auto closing = ledger.accumulating_month;
  std::map<std::uint32_t, std::uint64_t> month_figures;
  for (const auto& [key, seconds] : ledger.figures) {
    if (key.first == closing) month_figures.emplace(key.second, seconds);
  }
  const auto candidates = settlement_candidates(ledger, last_window);
  const auto settlement =
      settle_month(closing, candidates, month_figures, ledger.pool_payable);
  if (!settlement) return std::nullopt;
  if (!apply_settlement(ledger, *settlement)) return std::nullopt;
  if (!pool_failures({ledger.pool_accrued, ledger.pool_payable, ledger.pool_minted},
                     ledger.claims)
           .empty()) {
    return std::nullopt;
  }

  closed.settled = *settlement;
  // The empty indices the pass jumped, carried rather than iterated: they are
  // recorded so a trace can name them and so the bound is visible, and nothing
  // is done to them because there is nothing in them to do.
  for (std::uint32_t month = closing + 1; month < due_month; ++month) {
    closed.skipped.push_back(month);
  }
  return closed;
}

}  // namespace protocol::v9

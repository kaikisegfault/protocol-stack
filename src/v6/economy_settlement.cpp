#include "protocol/v6/economy.hpp"

namespace protocol::v6 {

std::uint64_t window_of_height(std::uint64_t height) {
  return height / kCycleBlocks;
}

bool accrues(std::uint64_t cycle_window, std::uint64_t mark) {
  return cycle_window <= mark + kMintAccumulationCap;
}

std::optional<WalkRange> walk_range(std::uint64_t mark,
                                    std::optional<std::uint64_t> last_assigned) {
  // ADR 0045's third derived rule. `NOTHING_TO_MINT` is the *empty range*
  // rather than the specification's literal "already equal, or none assigned":
  // a seat activated in window `w` holds mark `w` while the last assigned
  // window is `w - 2`, so under the literal reading that mint would proceed,
  // collect nothing, and then set the mark to `w - 2`. A mark that decreases
  // destroys the exactness argument the whole accumulation cap rests on.
  if (!last_assigned || mark >= *last_assigned) return std::nullopt;
  WalkRange range;
  range.first_window = mark + 1;
  range.last_window = *last_assigned < mark + kMintAccumulationCap
                          ? *last_assigned
                          : mark + kMintAccumulationCap;
  return range;
}

VerifiedUserCollection verified_user_collection(std::uint64_t minted_through_window,
                                                std::uint64_t enrolled_window,
                                                std::uint64_t height) {
  VerifiedUserCollection collection;
  collection.window_start = minted_through_window;
  collection.collectable_end = minted_through_window;

  const auto executing_window = window_of_height(height);
  // Before the first window closes nothing is completed, so nothing is
  // collectable. Version six's arithmetic subtracts one from the executing
  // window, and this is where that subtraction would go below zero.
  if (executing_window == 0) return collection;

  const auto last_completed = executing_window - 1;
  const auto period_end = enrolled_window + kVerifiedUserCycles - 1;
  const auto collectable_end =
      last_completed < period_end ? last_completed : period_end;
  if (collectable_end <= minted_through_window) return collection;

  // The cap forfeits here, and this is the line that makes it permanent: the
  // mark advances to `collectable_end` rather than to the walk's end, so the
  // windows before `window_start` are never issued.
  const auto capped_start = collectable_end - kMintAccumulationCap;
  collection.window_start = minted_through_window > capped_start
                                ? minted_through_window
                                : capped_start;
  collection.collectable_end = collectable_end;
  collection.count = collectable_end - collection.window_start;
  collection.amount_atomic = collection.count * kVerifiedUserDailyAtomic;
  return collection;
}

std::optional<std::uint64_t> verified_user_daily_atomic() {
  // The rate is derived rather than chosen, and that is the strongest thing
  // about it: the owner supplied the population, the period, and the cap, and
  // the three divide exactly. A remainder in either division would mean the
  // supplied figures do not determine the rate, so it is a refusal rather than
  // a rounding.
  if (kVerifiedUserChannelCapAtomic % kVerifiedUserPopulation != 0) {
    return std::nullopt;
  }
  const auto per_identity = kVerifiedUserChannelCapAtomic / kVerifiedUserPopulation;
  if (per_identity % kVerifiedUserCycles != 0) return std::nullopt;
  return per_identity / kVerifiedUserCycles;
}

std::uint64_t verified_user_remainder_at(std::uint64_t cycles) {
  // ADR 0042's figure: what the accepted cap leaves over at a period other than
  // 731. It is 420,000,000 atomic at 730 and zero at 731, which is what fixes
  // the period rather than making it a choice.
  return kVerifiedUserChannelCapAtomic % (kVerifiedUserPopulation * cycles);
}

}  // namespace protocol::v6

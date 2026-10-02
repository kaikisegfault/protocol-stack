// A kind-18 collection before window 31 takes what was earned, not thirty.
//
// `economy-transition-v6` states the collection over integers:
// `window_start = max(minted_through_window, collectable_end - 30)`. Before
// window 31 the second term is negative and the mark wins. **The kernel computed
// it in unsigned arithmetic**, so the term wrapped, won the maximum, and every
// kind-18 mint before window 31 collected exactly thirty daily permissions
// (ADR 0098). M4.2c's seeded network found it: Alice's mint at window 3 issued
// 5,130,000,000 atomic on four replicas and 342,000,000 in the model.
//
// No recorded vector reaches it, because no recorded kind-18 mint executes
// before window 31. So each figure below is the independent Python model's,
// `simulation.economy_transition_v6.verified_user.collect`, written out as a
// literal rather than derived here.

#include "economy_v9_execution_fixture.hpp"

namespace economy_v9_execution {

namespace {

struct Case {
  std::uint64_t enrolled_window;
  std::uint64_t mark;
  std::uint64_t executing_window;
  std::uint64_t window_start;
  std::uint64_t collectable_end;
  std::uint64_t count;
  std::uint64_t amount_atomic;
  const char* subject;
};

constexpr Case kCases[] = {
    {0, 0, 0, 0, 0, 0, 0, "nothing is completed in window 0"},
    {0, 0, 1, 0, 0, 0, 0, "window 0 is the airdrop's"},
    {0, 0, 2, 0, 1, 1, 171'000'000, "one window completed"},
    {0, 0, 3, 0, 2, 2, 342'000'000, "two windows completed, M4.2c's mint"},
    {0, 0, 30, 0, 29, 29, 4'959'000'000, "one below the cap"},
    {0, 0, 31, 0, 30, 30, 5'130'000'000, "exactly the cap"},
    {0, 0, 32, 1, 31, 30, 5'130'000'000, "one window forfeited"},
    {5, 5, 10, 5, 9, 4, 684'000'000, "a later enrollment, early"},
    {0, 25, 40, 25, 39, 14, 2'394'000'000, "a mark inside the cap"},
    {0, 0, 731, 700, 730, 30, 5'130'000'000, "the period's last window"},
    {0, 0, 800, 700, 730, 30, 5'130'000'000, "after the period"},
};

}  // namespace

void verify_verified_user_collection() {
  for (const auto& expected : kCases) {
    const auto actual = v9::verified_user_collection(
        expected.mark, expected.enrolled_window,
        expected.executing_window * v9::kCycleBlocks);
    pv::require(actual.window_start == expected.window_start &&
                    actual.collectable_end == expected.collectable_end &&
                    actual.count == expected.count &&
                    actual.amount_atomic == expected.amount_atomic,
                std::string("verified-user collection: ") + expected.subject);
  }
}

}  // namespace economy_v9_execution

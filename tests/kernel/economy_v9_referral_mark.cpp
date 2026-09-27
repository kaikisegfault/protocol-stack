// A referrer's first accrual starts its accumulation mark at the window before.
//
// `economy-transition-v3` creates a referral balance "with
// `collected_through_window` set to the window before that accrual, so a
// referrer is never capped before anything has been credited to them", and
// every version since carries the rule unchanged. **The kernel used to create it
// with a zero mark**, which is the same thing only while the first accrual lands
// inside the first thirty windows. After that a zero mark caps the referrer from
// their second accrual onward, and every later leg goes to the unreferred pool
// until they mint (ADR 0094).
//
// No recorded vector reaches it, because every recorded referral is minted in
// the block its first accrual lands in, and the mint moves the mark before any
// root commits to it. So this drives the assignment directly: a referred seat
// activated in window 100, thirty-one windows assigned in turn, and the balance
// and the pool read after each.

#include "economy_v9_execution_fixture.hpp"

namespace economy_v9_execution {

namespace {

constexpr std::uint32_t kReferredSeat = 0;
constexpr std::uint64_t kActivationWindow = 100;

v9::Ledger referred_ledger(const Octets32& referrer) {
  auto ledger = open_trace_ledger();
  v9::SeatRecord seat;
  seat.hub_identity_hash = repeated(0x71);
  seat.has_referrer = true;
  seat.referrer_hub_identity = referrer;
  seat.is_activated = true;
  seat.activation_height = kActivationWindow * v9::kCycleBlocks + 10;
  seat.minted_through_window = kActivationWindow;
  ledger.seats[kReferredSeat] = seat;
  return ledger;
}

void assign(v9::Ledger& ledger, std::uint64_t window) {
  const auto measured = v9::derive_schedule(ledger, window);
  pv::require(measured.size() == 1 && measured.front().in_span,
              "the referred seat is the one in-span seat");
  const auto assignment = v9::derive_assignment(ledger, window, measured);
  pv::require(assignment.has_value(), "the window assigns");
  pv::require(v9::apply_assignment(ledger, *assignment), "the assignment applies");
}

}  // namespace

void verify_referral_mark() {
  const auto referrer = repeated(0x72);
  auto ledger = referred_ledger(referrer);
  const auto first = kActivationWindow + 1;

  assign(ledger, first);
  const auto created = ledger.referral.find(referrer);
  pv::require(created != ledger.referral.end(), "the first accrual creates it");
  pv::require(created->second.collected_through_window == kActivationWindow,
              "the mark starts at the window before the first accrual");

  // Every window up to the mark plus the cap accrues to the referrer, the
  // second one included, which is the one a zero mark forfeited.
  const auto last_under_the_cap = kActivationWindow + v9::kMintAccumulationCap;
  for (auto window = first + 1; window <= last_under_the_cap; ++window) {
    assign(ledger, window);
  }
  const auto& balance = ledger.referral.at(referrer);
  pv::require(balance.accrued_atomic ==
                  v9::kMintAccumulationCap * v9::kReferralLegAtomic,
              "thirty windows accrue to the referrer");
  pv::require(ledger.pool_accrued == 0, "nothing reaches the unreferred pool");

  // The cap still binds, measured from that mark: the thirty-first window after
  // it is forfeited to the unreferred pool and stays inside the channel.
  assign(ledger, last_under_the_cap + 1);
  pv::require(ledger.referral.at(referrer).accrued_atomic ==
                  v9::kMintAccumulationCap * v9::kReferralLegAtomic,
              "the referrer over the cap accrues nothing");
  pv::require(ledger.pool_accrued == v9::kReferralLegAtomic &&
                  ledger.pool_payable == v9::kReferralLegAtomic,
              "the forfeited leg reaches the unreferred pool");
  pv::require(ledger.channel_outstanding[v9::kReferralChannel] ==
                  (v9::kMintAccumulationCap + 1) * v9::kReferralLegAtomic,
              "every leg stays in the referral channel");
}

}  // namespace economy_v9_execution

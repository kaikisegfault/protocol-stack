// The version-seven settlement: the recovery pool's arithmetic over the recorded
// schedule, the two seat sets, what a mint collects, and both identities.
//
// The schedule is fixture data — which seats are in scope, what each reported,
// and whether it is inside its own 731 cycles — so it is transcribed here and
// every figure it produces is compared against
// `test-vectors/economy-transition-v7.txt`, whose own side is derived from the
// specification's steps 5 through 7 rather than from the model's code.
//
// **The kernel runs its real derivation over a real ledger**, not a settlement
// stand-in: `derive_assignment` reads each seat's mark from the seat entry and
// `claimable` is the mint's own walk run once per seat, so a figure that agreed
// here and disagreed at a block would be a contradiction rather than a gap.

#include "economy_v7_fixture.hpp"

namespace economy_v7_fixture {
namespace {

// The recorded schedule's three uptimes, in seconds.
constexpr std::uint64_t kMet = 72'000;
constexpr std::uint64_t kBest = 79'200;
constexpr std::uint64_t kFailed = 3'600;

struct Measured {
  std::uint32_t seat_id;
  std::uint64_t uptime;
  bool in_span;
};

// window -> the seats measured in it, transcribed from the recorded schedule.
struct Window {
  std::uint64_t window;
  const char* name;
  std::vector<Measured> seats;
};

std::vector<Measured> in_span_seats(std::uint64_t uptime) {
  std::vector<Measured> seats;
  for (std::uint32_t seat = 0; seat < 7; ++seat) {
    seats.push_back({seat, uptime, true});
  }
  return seats;
}

std::vector<Measured> six_met_one_failed() {
  std::vector<Measured> seats;
  for (std::uint32_t seat = 0; seat < 6; ++seat) seats.push_back({seat, kMet, true});
  seats.push_back({6, kFailed, true});
  seats.push_back({9, kMet, false});
  return seats;
}

std::vector<Window> main_schedule() {
  std::vector<Window> windows;

  auto with_past = [](std::vector<Measured> seats, std::uint64_t uptime) {
    seats.push_back({9, uptime, false});
    return seats;
  };

  windows.push_back({2, "nobody_met_the_cycle",
                     with_past(in_span_seats(kFailed), kFailed)});
  windows.push_back({3, "a_machine_past_its_span_wins_outright",
                     with_past(in_span_seats(kMet), kBest)});
  windows.push_back({4, "a_seven_way_tie_leaves_dust_on_every_leg",
                     six_met_one_failed()});
  windows.push_back({5, "an_absorbed_pool_below_the_winner_count_is_returned_whole",
                     six_met_one_failed()});

  auto drained = six_met_one_failed();
  drained[0].uptime = kBest;
  windows.push_back({6, "one_winner_drains_the_pool", drained});

  windows.push_back({7, "nobody_met_the_cycle_again",
                     with_past(in_span_seats(kFailed), kFailed)});
  windows.push_back({8, "no_contributing_seat_and_the_pool_still_moves",
                     {{8, kMet, false}, {9, kMet, false}, {10, kMet, false}}});
  windows.push_back({9, "a_residual_survives_to_the_next_cycle",
                     with_past(in_span_seats(kMet), kMet)});
  return windows;
}

// A ledger holding nothing but what the two identities are stated over: every
// seat the schedule measures, activated with a zero mark, and the five channels.
v7::Ledger settlement_ledger() {
  v7::Ledger ledger;
  for (const std::uint32_t seat_id : {0U, 1U, 2U, 3U, 4U, 5U, 6U, 8U, 9U, 10U}) {
    v7::SeatRecord seat;
    seat.hub_identity_hash = kAliceIdentity;
    seat.is_activated = true;
    seat.minted_through_window = 0;
    ledger.seats[seat_id] = seat;
  }
  return ledger;
}

std::string legs(const v7::RecoveryPool& pool) {
  std::string out;
  for (std::size_t index = 0; index < v7::kRecoveryPoolLegs; ++index) {
    if (index != 0) out.push_back(',');
    out += std::to_string(pool[index]);
  }
  return out;
}

std::string seat_list(const std::vector<std::uint32_t>& seats) {
  if (seats.empty()) return "none";
  std::string out;
  for (std::size_t index = 0; index < seats.size(); ++index) {
    if (index != 0) out.push_back(',');
    out += std::to_string(seats[index]);
  }
  return out;
}

std::string window_list(const std::vector<std::uint64_t>& windows) {
  if (windows.empty()) return "none";
  std::string out;
  for (std::size_t index = 0; index < windows.size(); ++index) {
    if (index != 0) out.push_back(',');
    out += std::to_string(windows[index]);
  }
  return out;
}

std::uint64_t total(const v7::RecoveryPool& pool) {
  std::uint64_t sum = 0;
  for (const auto amount : pool) sum += amount;
  return sum;
}

// Run the recorded schedule and check every cycle's figures, then every state's
// two identities.
v7::Ledger verify_schedule(const pv::Values& values) {
  const auto schedule = main_schedule();
  pv::require(schedule.size() ==
                  expect_size(values, "settlement.schedule.cycle_count"),
              "the recorded schedule's cycle count");

  auto ledger = settlement_ledger();
  for (const auto& step : schedule) {
    const auto prefix = "settlement.w" + std::to_string(step.window) + ".";
    pv::require(expect_text(values, prefix + "name") == step.name,
                "the recorded cycle's name");

    std::vector<v7::SeatCycle> measured;
    for (const auto& seat : step.seats) {
      measured.push_back({seat.seat_id, seat.uptime, seat.in_span});
    }
    const auto before = ledger.pool;
    const auto assignment = v7::derive_assignment(ledger, step.window, measured);
    pv::require(assignment.has_value(), "the cycle derives");

    pv::require(assignment->in_scope_count ==
                    expect_size(values, prefix + "in_scope_count"),
                "the in-scope count");
    pv::require(seat_list(assignment->winners) ==
                    expect_text(values, prefix + "winners"),
                "the winner set");
    pv::require(seat_list(assignment->accrued) ==
                    expect_text(values, prefix + "accrued"),
                "the accrued set");
    pv::require(assignment->contributing_count ==
                    expect_number(values, prefix + "assigned_permissions"),
                "the contributing count");
    pv::require(assignment->reallocated_count ==
                    expect_number(values, prefix + "reallocated_count"),
                "the reallocated count");
    pv::require(legs(before) == expect_text(values, prefix + "pool_before"),
                "the pool the cycle found");
    pv::require(legs(assignment->pool_absorbed) ==
                    expect_text(values, prefix + "pool_absorbed"),
                "what the cycle absorbed");
    pv::require(legs(assignment->pool_after) ==
                    expect_text(values, prefix + "pool_after"),
                "the pool the next cycle finds");

    // A winner's pool share and the residual dividing it left behind, derived
    // here exactly as a mint derives them: from the absorbed amount and the
    // winner count, because the record commits to the absorbed amount alone.
    const auto winner_count = static_cast<std::uint32_t>(assignment->winners.size());
    v7::RecoveryPool share{};
    v7::RecoveryPool residual{};
    for (std::size_t channel = 0; channel < v7::kRecoveryPoolLegs; ++channel) {
      const auto taken = assignment->pool_absorbed[channel];
      share[channel] = winner_count == 0 ? 0 : taken / winner_count;
      residual[channel] = taken - share[channel] * winner_count;
    }
    pv::require(legs(share) == expect_text(values, prefix + "pool_share_per_winner"),
                "a winner's pool share");
    pv::require(legs(residual) == expect_text(values, prefix + "pool_residual"),
                "the residual dividing the pool left behind");

    const auto split = v7::split_permission(winner_count);
    v7::RecoveryPool dust{};
    for (std::size_t channel = 0; channel < v7::kRecoveryPoolLegs; ++channel) {
      dust[channel] = split.remainder[channel] * assignment->reallocated_count;
    }
    pv::require(legs(dust) == expect_text(values, prefix + "reallocation_dust"),
                "the reallocation dust");

    v7::RecoveryPool delta{};
    for (std::size_t channel = 0; channel < v7::kRecoveryPoolLegs; ++channel) {
      delta[channel] = v7::base_permission_leg(static_cast<std::uint8_t>(channel)) *
                       assignment->contributing_count;
    }
    pv::require(legs(delta) == expect_text(values, prefix + "outstanding_delta"),
                "what the cycle adds to outstanding");

    expect_true(values, prefix + "winners_are_the_top_of_the_eligible_set");
    expect_true(values, prefix + "assigned_permissions_is_the_contributing_count");

    pv::require(v7::apply_assignment(ledger, *assignment), "the cycle applies");

    // Both identities, after every cycle.
    const auto conservation = "conservation.w" + std::to_string(step.window) + ".";
    pv::require(ledger.assigned_permissions ==
                    expect_number(values, conservation + "assigned_permissions"),
                "the running assigned count");
    pv::require(total(ledger.pool) ==
                    expect_number(values, conservation + "pool_total"),
                "the pool total");
    std::uint64_t outstanding = 0;
    for (std::uint8_t channel = 0; channel < v7::kRecoveryPoolLegs; ++channel) {
      outstanding += ledger.channel_outstanding[channel];
    }
    pv::require(outstanding ==
                    expect_number(values, conservation + "outstanding_total"),
                "the outstanding total");
    const auto owed = v7::claimable(ledger);
    pv::require(owed.has_value(), "claimable derives");
    pv::require(total(*owed) ==
                    expect_number(values, conservation + "claimable_total"),
                "the claimable total");
    for (std::uint8_t channel = 0; channel < v7::kRecoveryPoolLegs; ++channel) {
      pv::require((*owed)[channel] + ledger.pool[channel] ==
                      ledger.channel_outstanding[channel],
                  "the backing identity holds after the cycle");
    }
    expect_true(values, conservation + "both_identities_hold");
  }
  return ledger;
}

void verify_sets(const pv::Values& values, const v7::Ledger& ledger) {
  // Window 3's winner is seat 9, which is past its own 731 cycles: it is in the
  // eligible set and not in the contributing set, and it took the whole pool
  // window 2 left behind. A winner derivation filtered by span would have
  // returned a different set there and an empty one at window 8, where no
  // contributing seat exists at all — and the pool would have stranded.
  const auto record = ledger.assignments.find(3);
  pv::require(record != ledger.assignments.end(), "window three has a record");
  const auto decoded = v7::decode_cycle_assignment_value(record->second);
  pv::require(decoded.has_value(), "window three's record decodes");
  pv::require(v7::bit_is_set(decoded->winner_bitmap, 9),
              "a seat past its span won the cycle");
  pv::require(!v7::bit_is_set(decoded->accrued_bitmap, 9),
              "and it accrued nothing, because it contributes nothing");
  pv::require(decoded->pool_absorbed[0] != 0, "that winner took the whole pool");

  const auto window8 = ledger.assignments.find(8);
  pv::require(window8 != ledger.assignments.end(), "window eight has a record");
  const auto eight = v7::decode_cycle_assignment_value(window8->second);
  pv::require(eight.has_value(), "window eight's record decodes");
  pv::require(eight->reallocated_count == 0 && eight->winner_count == 3,
              "window eight has no contributing seat and three winners");
  pv::require(eight->pool_absorbed[0] != 0, "and it still drained the pool");

  for (const auto* key : {"settlement.sets.eligible_holds_a_seat_the_contributing_set_does_not",
                          "settlement.sets.a_seat_past_its_span_won_the_cycle",
                          "settlement.sets.that_winner_took_the_whole_pool",
                          "settlement.sets.a_span_filtered_winner_set_would_differ",
                          "settlement.sets.a_span_filtered_winner_set_would_be_empty_at_window8",
                          "settlement.sets.window8_has_no_contributing_seat",
                          "settlement.sets.window8_still_drained_the_pool"}) {
    expect_true(values, key);
  }
}

void verify_collections(const pv::Values& values, v7::Ledger& ledger) {
  constexpr std::uint64_t kLastAssigned = 9;
  for (const std::uint32_t seat_id : {9U, 0U, 6U}) {
    const auto prefix = "collection.seat" + std::to_string(seat_id) + ".";
    auto& seat = ledger.seats[seat_id];
    const auto collection =
        v7::collect_node(ledger, seat_id, seat.minted_through_window, kLastAssigned);
    pv::require(collection.has_value(), "the walk derives");
    pv::require(legs(collection->per_channel) ==
                    expect_text(values, prefix + "per_channel"),
                "what the walk collects, per channel");
    pv::require(collection->total_atomic() ==
                    expect_number(values, prefix + "total_atomic"),
                "the collection total");
    pv::require(collection->windows_walked ==
                    expect_number(values, prefix + "windows_walked"),
                "the windows the walk covered");
    pv::require(window_list(collection->accrued_windows) ==
                    expect_text(values, prefix + "accrued_windows"),
                "the windows the seat accrued in");
    pv::require(window_list(collection->won_windows) ==
                    expect_text(values, prefix + "won_windows"),
                "the windows the seat won");

    for (std::uint8_t channel = 0; channel < v7::kRecoveryPoolLegs; ++channel) {
      const auto amount = collection->per_channel[channel];
      pv::require(ledger.channel_outstanding[channel] >= amount,
                  "a channel never issues more than it accrued");
      ledger.channel_outstanding[channel] -= amount;
      ledger.channel_issued[channel] += amount;
    }
    // The mark advances to the last assigned window whatever the walk found,
    // which is what makes the accumulation cap forfeit rather than defer.
    seat.minted_through_window = kLastAssigned;

    const auto owed = v7::claimable(ledger);
    pv::require(owed.has_value(), "claimable derives after the mint");
    for (std::uint8_t channel = 0; channel < v7::kRecoveryPoolLegs; ++channel) {
      pv::require((*owed)[channel] + ledger.pool[channel] ==
                      ledger.channel_outstanding[channel],
                  "the backing identity holds after the mint");
    }
  }
  // Seat 9 is past its own 731 cycles: it never accrued a bit and collected
  // only reallocation and pool shares, which is a conforming mint.
  expect_true(values, "collection.a_seat_past_its_span_collected_without_ever_accruing");
  expect_true(values, "collection.identities_hold_after_every_mint");
}

// One perturbed state, and the failure the invariant is required to name. The
// settlement ledger holds no registry, so it reports structural failures too;
// what matters is that the named one is among them.
void require_reports(const v7::Ledger& ledger, std::string_view failure) {
  const auto failures = v7::conservation_failures(ledger);
  pv::require(std::find(failures.begin(), failures.end(), failure) != failures.end(),
              "the invariant reports: " + std::string(failure));
}

void verify_final_identities(const pv::Values& values, const v7::Ledger& ledger) {
  const auto owed = v7::claimable(ledger);
  pv::require(owed.has_value(), "claimable derives at the final state");
  for (std::uint8_t channel = 0; channel < v7::kRecoveryPoolLegs; ++channel) {
    const auto prefix = "conservation.final.channel" + std::to_string(channel) + ".";
    pv::require(ledger.channel_issued[channel] ==
                    expect_number(values, prefix + "issued"),
                "the channel's issued total");
    pv::require(ledger.channel_outstanding[channel] ==
                    expect_number(values, prefix + "outstanding"),
                "the channel's outstanding total");
    pv::require((*owed)[channel] == expect_number(values, prefix + "claimable"),
                "what the channel still owes");
    pv::require(ledger.pool[channel] ==
                    expect_number(values, prefix + "recovery_pool"),
                "the channel's recovery pool leg");

    const auto assigned = ledger.assigned_permissions *
                          v7::base_permission_leg(channel);
    pv::require(assigned == expect_number(values, prefix + "assigned_total"),
                "what the manifest promised for the assigned cycles");
    pv::require(ledger.channel_issued[channel] +
                        ledger.channel_outstanding[channel] ==
                    assigned,
                "the channel identity holds");
    pv::require((*owed)[channel] + ledger.pool[channel] ==
                    ledger.channel_outstanding[channel],
                "the backing identity holds");
    expect_true(values, prefix + "channel_identity_holds");
    expect_true(values, prefix + "backing_identity_holds");
  }

  // **Both identities are the kernel's own invariant, not only this test's
  // arithmetic.** Checking them here and nowhere else would let
  // `conservation_failures` stop stating either one without a single vector
  // noticing, so each is broken on purpose and the invariant is required to
  // report it by name.
  auto stranded = ledger;
  stranded.pool[0] += 1;
  require_reports(stranded, "a Founder Node channel breaks the backing identity");
  auto created = ledger;
  created.channel_issued[0] += 1;
  require_reports(created, "a Founder Node channel breaks the channel identity");
}

}  // namespace

void verify_settlement(const pv::Values& values, const pv::Values& version_three,
                       const pv::Values& manifest) {
  // The imported half, against version three's own accepted record: version
  // seven replaces steps 5 through 7 and imports the rest, so a leg or a
  // threshold that moved would have to move in version three's file first.
  for (std::uint8_t channel = 0; channel < 5; ++channel) {
    const auto name = manifest.at("channel" + std::to_string(channel) + ".id");
    pv::require(v7::base_permission_leg(channel) ==
                    std::stoull(manifest.at("base_permission." + name)),
                "the base permission legs are the accepted manifest's");
  }
  pv::require(v7::kReferralLegAtomic ==
                  std::stoull(version_three.at("referral.leg_atomic")),
              "the referral leg is version three's");

  auto ledger = verify_schedule(values);
  verify_sets(values, ledger);
  verify_collections(values, ledger);
  verify_final_identities(values, ledger);
}

}  // namespace economy_v7_fixture

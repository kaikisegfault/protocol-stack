// The registry across a population: `simulation/economy_transition_v10/
// population.py`, rebuilt.
//
// The launch key retires when 100 machines meet one assigned cycle, and one
// founder's machines may sign 1,000 registrations a window between them. No
// recorded chain of blocks reaches either, because every in-scope seat is
// audited at every height. So these runs use version nine's evidence harness, as
// `economy-scenario-suite-v4` does:
//
// - transactions are admitted and executed by the kernel one at a time, at
//   heights the run sets;
// - each window opens through `open_window`, which is the prologue a block runs,
//   registry step included;
// - what a closed window's challenges would have written is supplied as its
//   kind-19 records, and a seat with no record is fully credited, as the
//   contract reads it.
//
// **Everything the vectors claim about the registry is derived by the kernel**:
// who met, the count, the retirement, every refusal, and every founder count a
// registration leaves. The harness supplies uptime and nothing else.
//
// **A refused transaction is checked for atomicity, and a bulk success is not**,
// as in the model: a thousand registrations each followed by a full root would
// cost more than the rest of the run together, and a bulk step that does not
// succeed fails the run, so no refusal is recorded without its root compared.

#include "economy_v10_execution_fixture.hpp"

#include <algorithm>

namespace economy_v10_execution {
namespace {

using Kind = v10::Kind;

// Seats buy capacity, not identities, so one person running a hundred machines
// is the ordinary case the limit exists for.
const Person& kFounder = kPopulationFounder;
constexpr std::uint64_t kActivationHeight = v10::kCycleBlocks - 10;
// A span run collects this often, so the accumulation cap never decides a
// cycle and the end of the span is the only thing that does.
constexpr std::uint64_t kSpanCollectionWindows = 20;

// Credited slots per seat in a window, where it is not all 24. Eighteen slots is
// exactly the threshold, and seventeen is one slot below it. The other founder's
// seat meets windows 1 and 2, so its machine is active in windows 3 and 4.
using Plan = std::map<std::uint64_t, std::map<std::uint32_t, std::uint32_t>>;

Plan cutoff_plan() {
  Plan plan;
  plan[1] = {{97, 18}, {98, 17}, {99, 12}};
  plan[2] = {{99, 6}};
  for (std::uint32_t seat = 50; seat < kMachines; ++seat) plan[3][seat] = 17;
  return plan;
}

class Driver {
 public:
  explicit Driver(Harness& harness)
      : harness_(&harness), build_(harness.signatures, harness.ledger) {}

  const Builder& build() const { return build_; }

  std::uint64_t at(std::uint64_t height) {
    pv::require(height >= harness_->ledger.height, "a harness height went backwards");
    harness_->ledger.height = height;
    harness_->ledger.timestamp = timestamp_of_height(height);
    return height;
  }

  std::uint64_t nonce(const Person& who) const {
    return nonce_of(harness_->ledger, who.escrow()) + 1;
  }

  // Admit and execute one transaction. An empty label is a bulk success.
  v10::Result submit(const std::string& label, const Bytes& raw) {
    auto& ledger = harness_->ledger;
    const auto verify = harness_->signatures.verifier();
    const auto admission = v10::admit(raw, ledger.chain_id, verify);
    pv::require(admission.admitted(), label + " was not admitted");
    std::optional<Hash> before;
    if (!label.empty()) {
      before = v10::ledger_state_root(ledger);
      // Required rather than compared, because two absent roots are equal and
      // the comparison below would then pass whatever the step did.
      pv::require(before.has_value(), label + " starts from a committable state");
    }
    const auto outcome = v10::execute(ledger, admission.transaction.envelope, verify);
    pv::require(outcome.has_value(), "no harness step is an invariant failure");
    if (outcome->succeeded()) tally(admission.transaction.envelope);
    if (label.empty()) {
      pv::require(outcome->succeeded(),
                  "a bulk step was refused: " + result_name(outcome->result));
      return outcome->result;
    }
    if (!outcome->succeeded()) {
      const auto after = v10::ledger_state_root(ledger);
      pv::require(after.has_value() && after == before,
                  "a refused " + label + " changed the state");
    }
    const auto receipt = v10::encode_receipt(v10::receipt_for(
        admission.transaction_id, admission.transaction.envelope, *outcome));
    pv::require(receipt.has_value(), "a receipt encodes");
    harness_->results[label] = result_name(outcome->result);
    harness_->receipts[label] = *receipt;
    return outcome->result;
  }

  void tally(const v10::Envelope& envelope) {
    if (envelope.kind != static_cast<std::uint8_t>(Kind::hub_register)) return;
    const auto body = v10::decode_body(envelope.kind, envelope.body);
    pv::require(body.has_value(), "an executed registration's body decodes");
    if (body->attesting_seat_id == v10::kLaunchAttester) return;
    const auto window = v10::window_of_height(harness_->ledger.height);
    harness_->attested[{window, body->attesting_seat_id}] += 1;
  }

  // Open `window`, then write the records of the window it closed.
  void open(std::uint64_t window, const Plan& plan) {
    at(window * v10::kCycleBlocks);
    auto outcome = v10::open_window(harness_->ledger);
    pv::require(outcome.has_value(),
                "window " + std::to_string(window) + " must open");
    harness_->windows[window] = std::move(*outcome);
    const auto closed = window - 1;
    const auto found = plan.find(closed);
    if (found == plan.end()) return;
    for (const auto& [seat_id, credited] : found->second) {
      const auto& seat = harness_->ledger.seats.at(seat_id);
      if (!v10::seat_in_scope(seat.activation_height, closed)) continue;
      v10::SeatWindowRecord record;
      record.credited = (std::uint32_t{1} << credited) - 1;
      const auto value = v10::seat_window_value(record);
      pv::require(value.has_value(), "a planned record encodes");
      harness_->ledger.uptime[v10::seat_window_key(closed, seat_id)] = *value;
    }
  }

  // Register each founder, sell and activate every seat, register every key.
  // `owners[seat_id]` is the seat's founder. The founders register under the
  // launch key in the order they first own a seat, and the first one's
  // registration is recorded.
  void seat_population(const std::vector<Person>& owners) {
    auto height = at(1);
    std::vector<Octets32> registered;
    for (const auto& owner : owners) {
      if (std::find(registered.begin(), registered.end(), owner.identity) !=
          registered.end()) {
        continue;
      }
      submit(registered.empty() ? "founder_registers" : "",
             build_.registration(owner, v10::kLaunchAttester, kLaunchKey,
                                 height + kLifetime));
      registered.push_back(owner.identity);
    }
    height = at(2);
    for (std::uint32_t seat_id = 0; seat_id < owners.size(); ++seat_id) {
      const auto& owner = owners[seat_id];
      submit("", build_.purchase(owner, seat_id, nonce(owner), height + kLifetime));
    }
    height = at(kActivationHeight);
    for (std::uint32_t seat_id = 0; seat_id < owners.size(); ++seat_id) {
      const auto& owner = owners[seat_id];
      submit("", build_.activation(owner, seat_id, nonce(owner), height + kLifetime));
    }
    height = at(kActivationHeight + 1);
    for (std::uint32_t seat_id = 0; seat_id < owners.size(); ++seat_id) {
      const auto& owner = owners[seat_id];
      submit("", build_.machine_registration(owner, seat_id, machine_key(seat_id),
                                             nonce(owner), height + kLifetime));
    }
  }

  // `count` new people, each attested by `seat_id`'s machine.
  void register_many(std::uint32_t seat_id, std::uint32_t first, std::uint32_t count) {
    const auto height = harness_->ledger.height;
    for (auto index = first; index < first + count; ++index) {
      submit("", build_.registration(person(index), seat_id, machine_key(seat_id),
                                     height + kLifetime));
    }
  }

  // The cutoff at 99, signatures crossed, and the founder's limit. The founder's
  // 1,000 are spread across two of their machines, 500 each, so neither machine
  // is near the figure alone. The 1,001st is refused on one of the two and on a
  // third machine that has attested nobody, while the other founder's machine
  // still signs.
  void window_three(std::uint64_t base) {
    const auto height = at(base + 1);
    const auto v = height + kLifetime;
    submit("launch.still_signs_at_ninety_nine",
           build_.registration(person(1), v10::kLaunchAttester, kLaunchKey, v));
    submit("crossed.a_key_signing_for_another_seat",
           build_.registration(person(2), 2, machine_key(1), v));
    submit("crossed.a_genuine_signature_under_another_seat",
           build_.registration(person(2), 2, machine_key(1), v, 1));
    const auto half = v10::kFounderRegistrationsPerWindow / 2;
    submit("limit.the_first", build_.registration(person(10), 0, machine_key(0), v));
    register_many(0, 11, half - 1);
    register_many(1, 10 + half, half - 1);
    const auto last = 10 + v10::kFounderRegistrationsPerWindow - 1;
    submit("limit.the_thousandth",
           build_.registration(person(last), 1, machine_key(1), v));
    const auto count = harness_->ledger.founder_registrations.at(kFounder.identity);
    pv::require(count.registration_window == 3, "the founder's count is window 3's");
    harness_->count_after_the_thousandth = count.registrations_in_window;
    submit("limit.a_forgery_naming_a_full_founders_machine",
           build_.registration(person(last + 1), 2, machine_key(0), v));
    submit("limit.the_thousand_and_first",
           build_.registration(person(last + 1), 0, machine_key(0), v));
    submit("limit.a_machine_that_attested_nobody",
           build_.registration(person(last + 1), 2, machine_key(2), v));
    submit("crossed.a_full_founders_signature_under_another_founders_seat",
           build_.registration(person(last + 1), kOtherFounderSeat, machine_key(0), v,
                               0));
    submit("limit.another_founders_machine_still_signs",
           build_.registration(person(last + 1), kOtherFounderSeat,
                               machine_key(kOtherFounderSeat), v));
  }

  // A key one founder released, re-registered on the other founder's seat. A
  // signature that key made for seat 1 is refused under seat 100, because the
  // registration message binds the seat, and a signature it makes for seat 100
  // is accepted. Without the binding the first would verify too, and count
  // against the founder who did not sign it.
  void released_key(std::uint64_t height) {
    const auto v = height + kLifetime;
    const auto released = machine_key(1);
    submit("", build_.machine_registration(kFounder, 1, machine_key(1, 1),
                                           nonce(kFounder), v));
    submit("", build_.machine_registration(kOtherFounder, kOtherFounderSeat,
                                           released, nonce(kOtherFounder), v));
    submit("crossed.a_released_keys_signature_for_its_old_seat",
           build_.registration(person(9'004), kOtherFounderSeat, released, v, 1));
    submit("crossed.the_released_key_signs_for_its_new_seat",
           build_.registration(person(9'004), kOtherFounderSeat, released, v));
  }

 private:
  Harness* harness_;
  Builder build_;
};

}  // namespace

// 101 machines, the count at 99 and then 100, the founder's limit, and the cap.
Harness cutoff_run() {
  Harness harness;
  harness.ledger = open_trace_ledger();
  Driver driver(harness);
  std::vector<Person> owners(kOtherFounderSeat, kFounder);
  owners.push_back(kOtherFounder);
  driver.seat_population(owners);
  const auto plan = cutoff_plan();
  for (std::uint64_t window = 1; window <= kCapRunWindow; ++window) {
    driver.open(window, plan);
    const auto base = window * v10::kCycleBlocks;
    if (window == 2) {
      // The window-0 assignment has just run, with every key registered and no
      // seat in scope: the state the count's exclusion of a zero mark is about.
      std::uint64_t unmarked = 0;
      for (const auto& [seat_id, entry] : harness.ledger.machine_keys) {
        (void)seat_id;
        if (entry.last_met_window == 0) unmarked += 1;
      }
      harness.unmarked_at_the_window_0_assignment = unmarked;
    } else if (window == 3) {
      driver.window_three(base);
    } else if (window == 4) {
      const auto height = driver.at(base + 1);
      driver.submit("launch.refused_once_retired",
                    driver.build().registration(person(9'001), v10::kLaunchAttester,
                                                kLaunchKey, height + kLifetime));
      driver.submit("limit.the_count_restarts_in_the_next_window",
                    driver.build().registration(person(9'002), 0, machine_key(0),
                                                height + kLifetime));
      driver.released_key(height);
    } else if (window == 5) {
      const auto height = driver.at(base + 1);
      driver.submit("launch.not_revived_when_the_count_falls",
                    driver.build().registration(person(9'003), v10::kLaunchAttester,
                                                kLaunchKey, height + kLifetime));
    }
  }
  return harness;
}

// One machine, every slot credited, past the end of its seat's 731 cycles.
Harness span_run() {
  Harness harness;
  harness.ledger = open_trace_ledger();
  Driver driver(harness);
  driver.seat_population({kFounder});
  for (std::uint64_t window = 1; window <= kSpanRunWindow; ++window) {
    driver.open(window, {});
    if (window % kSpanCollectionWindows == 0) {
      const auto height = driver.at(window * v10::kCycleBlocks + 1);
      driver.submit("", driver.build().mint(kFounder, Kind::mint_node,
                                            driver.nonce(kFounder),
                                            height + kLifetime, 0));
    }
  }
  return harness;
}

}  // namespace economy_v10_execution

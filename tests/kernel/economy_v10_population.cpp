// The registry across a population: `simulation/economy_transition_v10/
// population.py`, rebuilt.
//
// The launch key retires when 100 machines meet one assigned cycle, and a machine
// may sign 1,000 registrations a window. No recorded chain of blocks reaches
// either, because every in-scope seat is audited at every height. So these runs
// use version nine's evidence harness, as `economy-scenario-suite-v4` does:
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
// who met, the count, the retirement, every refusal, and every count a
// registration leaves. The harness supplies uptime and nothing else.
//
// **A refused transaction is checked for atomicity, and a bulk success is not**,
// as in the model: a thousand registrations each followed by a full root would
// cost more than the rest of the run together, and a bulk step that does not
// succeed fails the run, so no refusal is recorded without its root compared.

#include "economy_v10_execution_fixture.hpp"

namespace economy_v10_execution {
namespace {

using Kind = v10::Kind;

// One founder holds every seat. Seats buy capacity, not identities, so one
// person running many machines is the ordinary case the limit exists for.
const Person kFounder = person(0);
constexpr std::uint64_t kActivationHeight = v10::kCycleBlocks - 10;
// A span run collects this often, so the accumulation cap never decides a
// cycle and the end of the span is the only thing that does.
constexpr std::uint64_t kSpanCollectionWindows = 20;

// Credited slots per seat in a window, where it is not all 24. Eighteen slots is
// exactly the threshold, and seventeen is one slot below it.
using Plan = std::map<std::uint64_t, std::map<std::uint32_t, std::uint32_t>>;

Plan cutoff_plan() {
  Plan plan;
  plan[1] = {{98, 18}, {99, 17}, {100, 12}};
  plan[2] = {{100, 6}};
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
    if (!label.empty()) before = v10::ledger_state_root(ledger);
    const auto outcome = v10::execute(ledger, admission.transaction.envelope, verify);
    pv::require(outcome.has_value(), "no harness step is an invariant failure");
    if (label.empty()) {
      pv::require(outcome->succeeded(),
                  "a bulk step was refused: " + result_name(outcome->result));
      return outcome->result;
    }
    if (!outcome->succeeded()) {
      pv::require(v10::ledger_state_root(ledger) == before,
                  "a refused " + label + " changed the state");
    }
    const auto receipt = v10::encode_receipt(v10::receipt_for(
        admission.transaction_id, admission.transaction.envelope, *outcome));
    pv::require(receipt.has_value(), "a receipt encodes");
    harness_->results[label] = result_name(outcome->result);
    harness_->receipts[label] = *receipt;
    return outcome->result;
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

  // Register the founder, sell and activate every seat, register every key.
  void seat_population(std::uint32_t machines) {
    submit("founder_registers",
           build_.registration(kFounder, v10::kLaunchAttester, kLaunchKey,
                               at(1) + kLifetime));
    auto height = at(2);
    for (std::uint32_t seat_id = 0; seat_id < machines; ++seat_id) {
      submit("", build_.purchase(kFounder, seat_id, nonce(kFounder), height + kLifetime));
    }
    height = at(kActivationHeight);
    for (std::uint32_t seat_id = 0; seat_id < machines; ++seat_id) {
      submit("", build_.activation(kFounder, seat_id, nonce(kFounder),
                                   height + kLifetime));
    }
    height = at(kActivationHeight + 1);
    for (std::uint32_t seat_id = 0; seat_id < machines; ++seat_id) {
      submit("", build_.machine_registration(kFounder, seat_id, machine_key(seat_id),
                                             nonce(kFounder), height + kLifetime));
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

  // The cutoff at 99, two machines' signatures crossed, and the limit.
  void window_three(std::uint64_t base) {
    const auto height = at(base + 1);
    const auto v = height + kLifetime;
    submit("launch.still_signs_at_ninety_nine",
           build_.registration(person(1), v10::kLaunchAttester, kLaunchKey, v));
    submit("crossed.a_key_signing_for_another_seat",
           build_.registration(person(2), 2, machine_key(1), v));
    submit("crossed.a_genuine_signature_under_another_seat",
           build_.registration(person(2), 2, machine_key(1), v, 1));
    submit("limit.the_first", build_.registration(person(10), 0, machine_key(0), v));
    register_many(0, 11, v10::kMachineRegistrationsPerWindow - 2);
    const auto last = 11 + v10::kMachineRegistrationsPerWindow - 2;
    submit("limit.the_thousandth",
           build_.registration(person(last), 0, machine_key(0), v));
    harness_->count_after_the_thousandth =
        harness_->ledger.machine_keys.at(0).registrations_in_window;
    submit("limit.a_forgery_naming_a_full_machine",
           build_.registration(person(last + 1), 0, machine_key(1), v));
    submit("limit.the_thousand_and_first",
           build_.registration(person(last + 1), 0, machine_key(0), v));
    submit("limit.another_machine_still_signs",
           build_.registration(person(last + 1), 1, machine_key(1), v));
  }

 private:
  Harness* harness_;
  Builder build_;
};

}  // namespace

// 101 machines, the count at 99 and then 100, the limit, and the cap.
Harness cutoff_run() {
  Harness harness;
  harness.ledger = open_trace_ledger();
  Driver driver(harness);
  driver.seat_population(kMachines);
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
  driver.seat_population(1);
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

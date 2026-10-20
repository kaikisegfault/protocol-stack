// Three rules no recorded vector reaches, each found by a mutation probe that
// the vectors let pass.
//
// **The lifetime rule's place among the shared checks.** The specification
// orders them: the fee limit, the expiry, the lifetime, the nonce pair, then the
// debit pair. Every lifetime refusal the chain records carries a correct fee
// limit and a correct nonce, so moving the rule after the nonce checks, or ahead
// of the fee limit, changed no recorded value. Its place relative to `EXPIRED`
// needs no check: a refusal there needs `valid_until < h`, and the lifetime
// needs `valid_until > h + 1,200`, so no transaction fails both.
//
// **An unmarked machine is not active while window 0 is the latest assigned
// one.** A mark of 0 means none, and through window 2 the most recently
// assigned window is 0 too, so an activity test that compared the two without
// excluding 0 would call every new machine active for a day. No recorded run
// registers through a machine in window 2. ADR 0103 excludes a zero mark from
// the count; this is the same rule applied to activity, which the specification
// states as "nonzero and equals".
//
// **`open_window` opens only a window.** It is the harness's entry point, and a
// harness that called it at any other height would run a prologue no chain runs.

#include "economy_v10_execution_fixture.hpp"

namespace economy_v10_execution {
namespace {

using Kind = v10::Kind;

// A ledger driven a transaction at a time at heights the check sets, the
// population harness's shape without its recording.
class Bench {
 public:
  Bench() : ledger_(open_trace_ledger()), build_(signatures_, ledger_) {}

  v10::Ledger& ledger() { return ledger_; }
  const Builder& build() const { return build_; }

  std::uint64_t at(std::uint64_t height) {
    pv::require(height >= ledger_.height, "a bench height went backwards");
    ledger_.height = height;
    ledger_.timestamp = timestamp_of_height(height);
    return height;
  }

  v10::Result submit(const Bytes& raw) {
    const auto verify = signatures_.verifier();
    const auto admission = v10::admit(raw, ledger_.chain_id, verify);
    pv::require(admission.admitted(), "a bench transaction is admitted");
    const auto before = v10::ledger_state_root(ledger_);
    const auto outcome = v10::execute(ledger_, admission.transaction.envelope, verify);
    pv::require(outcome.has_value(), "no bench step is an invariant failure");
    if (!outcome->succeeded()) {
      pv::require(v10::ledger_state_root(ledger_) == before,
                  "a refusal changed the state");
    }
    return outcome->result;
  }

  void open(std::uint64_t window) {
    at(window * v10::kCycleBlocks);
    pv::require(v10::open_window(ledger_).has_value(), "the window opens");
  }

 private:
  Signatures signatures_;
  v10::Ledger ledger_;
  Builder build_;
};

void require_result(v10::Result derived, v10::Result expected,
                    const std::string& what) {
  pv::require(derived == expected, what + ": derived " + result_name(derived) +
                                       ", expected " + result_name(expected));
}

}  // namespace

void verify_lifetime_order() {
  Bench bench;
  const auto& build = bench.build();
  require_result(bench.submit(build.registration(kAlice, v10::kLaunchAttester,
                                                 kLaunchKey, bench.at(1) + kLifetime)),
                 v10::Result::success, "Alice registers");
  const auto h = bench.at(2);
  const auto beyond = h + kLifetime + 1;

  // The fee limit is checked first, so a purchase that fails both is refused
  // for its fee limit.
  v10::Body body;
  body.seat_id = 0;
  body.hub_signature = Bytes(v10::kSignatureBytes, 0);
  auto low = build.transaction(Kind::purchase_seat, kAlice.signer_key, 1, body, beyond);
  low.fee_limit = kFixedFee - 1;
  require_result(bench.submit(build.sign(build.approve(low, kAlice.hub_key))),
                 v10::Result::fee_limit_too_low,
                 "a low fee limit past the lifetime");

  // The lifetime precedes the nonce pair, and therefore the debit pair after it.
  // The control shows the nonce really is one the escrow does not expect.
  require_result(bench.submit(build.purchase(kAlice, 0, 5, beyond)),
                 v10::Result::approval_lifetime_exceeded,
                 "an unexpected nonce past the lifetime");
  require_result(bench.submit(build.purchase(kAlice, 0, 5, h + kLifetime)),
                 v10::Result::nonce_mismatch, "the same nonce within the lifetime");
}

void verify_unmarked_machine_in_window_two() {
  Bench bench;
  const auto& build = bench.build();
  const auto founder = person(0);
  require_result(bench.submit(build.registration(founder, v10::kLaunchAttester,
                                                 kLaunchKey, bench.at(1) + kLifetime)),
                 v10::Result::success, "the founder registers");
  require_result(bench.submit(build.purchase(founder, 0, 1, bench.at(2) + kLifetime)),
                 v10::Result::success, "the seat is bought");
  require_result(bench.submit(build.activation(founder, 0, 2,
                                               bench.at(v10::kCycleBlocks - 10) +
                                                   kLifetime)),
                 v10::Result::success, "the seat is activated");
  require_result(bench.submit(build.machine_registration(
                     founder, 0, machine_key(0), 3,
                     bench.at(v10::kCycleBlocks - 9) + kLifetime)),
                 v10::Result::success, "the machine key is registered");

  // Window 2's opening assigns window 0, in which no seat is in scope, so the
  // key stays unmarked while the latest assigned window is 0.
  bench.open(1);
  bench.open(2);
  auto h = bench.at(2 * v10::kCycleBlocks + 1);
  pv::require(bench.ledger().machine_keys.at(0).last_met_window == 0 &&
                  v10::last_assigned_window(h) == 0,
              "an unmarked key while window 0 is the latest assigned");
  pv::require(!v10::machine_active(bench.ledger(), 0), "an unmarked machine is idle");
  require_result(bench.submit(build.registration(person(1), 0, machine_key(0),
                                                 h + kLifetime)),
                 v10::Result::machine_not_active, "an unmarked machine attests");

  // The control: window 3's opening assigns window 1, where the seat ran every
  // slot, so the same machine is marked and signs.
  bench.open(3);
  h = bench.at(3 * v10::kCycleBlocks + 1);
  pv::require(v10::machine_active(bench.ledger(), 0), "a machine that met is active");
  require_result(bench.submit(build.registration(person(1), 0, machine_key(0),
                                                 h + kLifetime)),
                 v10::Result::success, "a marked machine attests");
}

void verify_open_window_refusals() {
  Bench bench;
  auto& ledger = bench.ledger();
  const auto root = v10::ledger_state_root(ledger);

  bench.at(1);
  pv::require(!v10::open_window(ledger).has_value(),
              "a height that opens no window is refused");
  pv::require(ledger.height == 1 && ledger.window_months.size() == 1,
              "a refusal leaves the ledger where it was");

  // The window-1 height with a stamp one millisecond past calendar-v1's range.
  ledger.height = v10::kCycleBlocks;
  ledger.timestamp = v10::kMaxTimestampMillis + 1;
  pv::require(!v10::open_window(ledger).has_value(),
              "a stamp outside the calendar's range is refused");
  pv::require(!ledger.window_months.contains(1), "the refused window did not open");

  // The same height with the chain's own stamp opens it.
  ledger.timestamp = timestamp_of_height(v10::kCycleBlocks);
  const auto opened = v10::open_window(ledger);
  pv::require(opened.has_value() && opened->opened_window == 1 &&
                  !opened->active_machines.has_value(),
              "window 1 opens, below the lag, with no registry step");
  pv::require(root.has_value(), "the genesis state is committable");
}

}  // namespace economy_v10_execution

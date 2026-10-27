#pragma once

// The version-ten application layer: what turns the version-ten owning store
// into something a consensus engine can drive.
//
// **It is version nine's application with the namespace and the store rebound**
// (ADR 0110), under `consensus-application-v3`. The seven operations, the
// ownership and staging rules, and the terminal-refusal rule are version eight's
// and are unchanged. The clock is version nine's, and almost everything
// interesting here is about keeping it in one place. What version ten changes is
// the ledger behind it: the protocol version Info reports, the application state
// InitChain expects, and the five result codes `application_code` maps to `301`
// through `305`.
//
// **`process_proposal` is the only operation that reads one, and it reads one
// once.** It returns an eight-value *decision* under a zero status rather than an
// error, because a peer proposing a bad timestamp is an ordinary event on a live
// network and a contract that made it an application exception would let one
// malformed proposal stop a correct machine.
//
// **`finalize_block` applies C1 and C2 and cannot apply C5.** That is structural
// rather than promised: it calls `v10::replay_timestamp`, which takes no clock
// argument, and the clock source is not reachable from it. A machine that
// re-applied the tolerance on the replay path would reject the chain's own past
// one tolerance-width after producing it, and every correct replica would do so
// at a different moment. The failure is silent, which is why the separation is
// enforced by a signature rather than by a comment.
//
// **There is deliberately no status for either C5 condition**, and a conforming
// test asserts the absence. A status space containing a tolerance value is a
// status space with a tolerance reachable on the replay path, which is the defect
// this separation exists to prevent.

#include "protocol/application/application_v1.hpp"
#include "protocol/storage/sqlite_ledger_v10.hpp"
#include "protocol/v10/ledger.hpp"

#include <cstdint>
#include <functional>
#include <memory>
#include <span>
#include <variant>
#include <vector>

namespace protocol::application {

inline constexpr std::uint64_t kApplicationProtocolVersionV10 = 10;

// Version ten's own bound on raw inputs is the kernel's, as version nine's is.
inline constexpr std::size_t kMaximumBlockInputsV10 = protocol::v10::kMaxRawInputs;

// **`ProcessProposal`'s eight outcomes**, version nine's, suffixed because both
// versions' headers are included together while ADR 0104 stages them. Values
// `0` through `5` are exactly `calendar-v1`'s ordered conditions in its own
// numbering, which is why `decision_of` is a cast rather than a translation
// table; `6` and `7` are this contract's own and are numbered after the last
// kernel condition.
//
// The adapter votes ACCEPT on `accepted` and REJECT on everything else. The extra
// information is safe because it is not consensus-visible: ABCI ProcessProposal
// transports ACCEPT or REJECT and nothing else, so the byte reaches logs and
// tests and never reaches a peer.
enum class ProposalDecisionV10 : std::uint8_t {
  accepted = 0,
  height_not_next = 1,
  timestamp_range = 2,
  timestamp_not_monotonic = 3,
  timestamp_ahead_of_tolerance = 4,
  timestamp_behind_tolerance = 5,
  resource_bound = 6,
  not_executable = 7,
};

// **The assertion the contract requires.** A later version adding a sixth kernel
// condition would otherwise silently alias `resource_bound`, because the mapping
// is positional. This makes that a build failure.
static_assert(protocol::v10::kTimestampConditionCount == 6,
              "a kernel condition was added and would alias resource_bound");

constexpr ProposalDecisionV10 decision_of(
    protocol::v10::TimestampCondition condition) noexcept {
  return static_cast<ProposalDecisionV10>(static_cast<std::uint8_t>(condition));
}

// **The two fatal timestamp statuses, reachable only from `finalize_block`.**
// Kind 5 reports the same two conditions as decisions `2` and `3` under a zero
// status, because there the correct response is a vote and here it is a halt:
// `finalize_block` is only ever called on a block the network already decided, so
// a C1 or C2 failure means this machine's rules and the network's decision
// disagree about history.
//
// They extend `ApplicationError`'s numbering rather than replacing it, and there
// is no third and fourth value: C5 has no status because C5 has no path here.
enum class TimestampFailureV10 : std::uint16_t {
  decided_block_failed_range = 7,
  decided_block_failed_monotonicity = 8,
};

// Version one's `256 + r` over version ten's fifty results, so the five codes
// version ten adds land at `301` through `305` and the range ends there.
constexpr std::uint32_t application_code(protocol::v10::Result result) noexcept {
  const auto value = static_cast<std::uint32_t>(result);
  return value == 0 ? 0 : 256U + value;
}

// **The durable head is two scalars and a root**, so every place version eight
// reported a height, this reports the height and the stamp. The stamp is
// redundant against the root and is reported anyway: the root commits to it, so
// two agreeing roots already imply agreeing stamps, but a root is a hash and
// proves agreement without showing the value. Reporting it makes a divergence
// diagnosable rather than merely detectable.
struct ApplicationInfoV10 {
  std::uint64_t application_version = 0;
  std::uint64_t height = 0;
  std::uint64_t timestamp = 0;
  protocol::v10::Hash state_root{};

  bool operator==(const ApplicationInfoV10&) const = default;
};

struct FinalizedBlockV10 {
  protocol::v10::Hash state_root{};
  protocol::v10::Hash block_id{};
  std::vector<TransactionResult> transaction_results;

  bool operator==(const FinalizedBlockV10&) const = default;
};

struct CommittedHeadV10 {
  std::uint64_t height = 0;
  std::uint64_t timestamp = 0;
  protocol::v10::Hash state_root{};

  bool operator==(const CommittedHeadV10&) const = default;
};

// A decided block whose stamp this machine's rules refuse. It is not an
// `ApplicationError` because it is not one of version one's six; it is fatal for
// its own reason and names which of the two rules failed.
using FinalizeFailureV10 = std::variant<ApplicationError, TimestampFailureV10>;

using InfoResultV10 = std::variant<ApplicationInfoV10, ApplicationError>;
using InitChainResultV10 = std::variant<protocol::v10::Hash, ApplicationError>;
using TransactionCheckResultV10 =
    std::variant<TransactionResult, ApplicationError>;
using PrepareProposalResultV10 = std::variant<PreparedProposal, ApplicationError>;
// A decision is returned under a zero status; only a statement about *this
// machine* — not yet initialised, already staged, terminal — is an error.
using ProcessProposalResultV10 =
    std::variant<ProposalDecisionV10, ApplicationError>;
using FinalizeBlockResultV10 = std::variant<FinalizedBlockV10, FinalizeFailureV10>;
using CommitResultV10 = std::variant<CommittedHeadV10, ApplicationError>;

// The bound clock source. A deployment that cannot read a clock cannot vote on a
// proposal and must fail to start rather than vote on an assumed value, so this
// is supplied at construction and never defaulted.
using ClockSourceV10 = std::function<std::uint64_t()>;

struct ApplicationV10Result;

class ApplicationV10 {
 public:
  ~ApplicationV10() noexcept;
  ApplicationV10(ApplicationV10&&) noexcept;

  ApplicationV10(const ApplicationV10&) = delete;
  ApplicationV10& operator=(const ApplicationV10&) = delete;
  ApplicationV10& operator=(ApplicationV10&&) = delete;

  InfoResultV10 info() const;
  // Four values are compared, as version nine compares them: the chain, the
  // initial height, the genesis stamp, and the application state.
  // **C1 is applied and no clock is read.** The stamp is compared against the
  // validated canonical genesis; applying a tolerance here would make a chain
  // un-initialisable one tolerance-width after its genesis was written, which is
  // to say would make every chain un-restartable.
  InitChainResultV10 init_chain(const protocol::v10::Octets32& chain_id,
                               std::uint64_t initial_height,
                               std::uint64_t genesis_timestamp,
                               std::span<const std::uint8_t> app_state);
  TransactionCheckResultV10 check_transaction(
      std::span<const std::uint8_t> raw_transaction) const;
  PrepareProposalResultV10 prepare_proposal(
      std::int64_t maximum_transaction_bytes,
      std::span<const protocol::v10::Bytes> transactions) const;
  // **The one operation that reads the bound clock, and it reads it once.**
  // `calendar-v1`'s ordered conditions run before the resource bounds: the vote
  // is identical under either order, so this decides only what is *reported*, and
  // a proposal failing both should report what the normative order says fires
  // first.
  ProcessProposalResultV10 process_proposal(
      std::uint64_t height, std::uint64_t timestamp,
      std::span<const protocol::v10::Bytes> transactions) const;
  // **No clock parameter, and none reachable.** C1 and C2 are applied through
  // `replay_timestamp`; C5 is not applied and cannot be.
  FinalizeBlockResultV10 finalize_block(
      std::uint64_t height, std::uint64_t timestamp,
      std::span<const protocol::v10::Bytes> transactions);
  CommitResultV10 commit();

 private:
  struct Impl;

  explicit ApplicationV10(std::unique_ptr<Impl> implementation) noexcept;

  friend ApplicationV10Result make_application_v10(
      protocol::storage::SQLiteLedgerV10 ledger, ClockSourceV10 clock);

  std::unique_ptr<Impl> implementation_;
};

struct ApplicationV10Result {
  std::variant<ApplicationV10, ApplicationError> result;
};

// The application takes the store by value, for version eight's reason: one local
// writer is ADR 0007's contract, and an application that did not own its store
// could not promise that the head it staged against is the head it commits to.
//
// **The clock has no default.** A defaulted system clock would make "this
// deployment cannot read a clock" unrepresentable, and the contract requires such
// a deployment to fail to start rather than vote on an assumed value. An empty
// `clock` is refused here.
ApplicationV10Result make_application_v10(
    protocol::storage::SQLiteLedgerV10 ledger, ClockSourceV10 clock);

}  // namespace protocol::application

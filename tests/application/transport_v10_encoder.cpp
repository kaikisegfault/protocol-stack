// The version-ten response encoder on its own, where every value the contract
// names can be produced — including the two decisions and four statuses the
// application cannot be made to produce over the wire.
//
// **The refusals each carry a control.** A version-nine receipt is refused, and
// the same receipt with its version octet at `10` is written; a result byte of
// `50` is refused, and one of `49` is written under `305`; a timestamp status is
// refused through the `ApplicationError` path, and written through its own. A
// refusal without the accepted case beside it would pass against an encoder that
// refused everything.

#include "protocol/application/response_v10.hpp"

#include "transport_v10_support.hpp"

#include <string>
#include <variant>

namespace transport_v10_tests {
namespace {

Response require_encoded(const pa::EncodedFrameResult& result, pa::MessageKind kind,
                         std::uint64_t request_id, const std::string& subject) {
  pv::require(std::holds_alternative<Bytes>(result), subject + ": did not encode");
  return read_response(std::get<Bytes>(result), kind, request_id, subject);
}

void require_refused(const pa::EncodedFrameResult& result, const std::string& subject) {
  pv::require(std::holds_alternative<pa::WireError>(result) &&
                  std::get<pa::WireError>(result) == pa::WireError::invalid_payload,
              subject + ": was written");
}

constexpr pa::MessageKind kKinds[] = {
    pa::MessageKind::info,          pa::MessageKind::init_chain,
    pa::MessageKind::check_transaction, pa::MessageKind::prepare_proposal,
    pa::MessageKind::process_proposal,  pa::MessageKind::finalize_block,
    pa::MessageKind::commit,
};

// Every decision `0` through `7` is its own octet under status zero, and nothing
// past `7` is written.
void check_decisions() {
  for (std::uint8_t raw = 0; raw <= 7; ++raw) {
    const auto subject = "decision " + std::to_string(raw);
    const auto response = require_encoded(
        pa::encode_success_response_v10(
            pa::MessageKind::process_proposal, raw + 1U,
            pa::SuccessResponseV10{static_cast<pa::ProposalDecisionV10>(raw)}),
        pa::MessageKind::process_proposal, raw + 1U, subject);
    pv::require(response.status == 0 && response.body == Bytes{raw},
                subject + ": is not its own octet under status zero");
  }
  for (const std::uint8_t raw : {std::uint8_t{8}, std::uint8_t{255}}) {
    require_refused(pa::encode_success_response_v10(
                        pa::MessageKind::process_proposal, 1,
                        pa::SuccessResponseV10{static_cast<pa::ProposalDecisionV10>(raw)}),
                    "decision " + std::to_string(raw));
  }
}

// Statuses `1` through `6` for every kind; `7` and `8` for kind 6 through the one
// function that can write them, and through nothing else.
void check_statuses() {
  for (const auto kind : kKinds) {
    for (std::uint16_t status = 1; status <= 6; ++status) {
      const auto subject = "status " + std::to_string(status) + " on kind " +
                           std::to_string(static_cast<unsigned>(kind));
      const auto response = require_encoded(
          pa::encode_error_response_v10(kind, 9, static_cast<pa::ApplicationError>(status)),
          kind, 9, subject);
      pv::require(response.status == status, subject + ": the wrong status");
    }
    for (const std::uint16_t status : {0, 7, 8}) {
      require_refused(
          pa::encode_error_response_v10(kind, 9, static_cast<pa::ApplicationError>(status)),
          "an ApplicationError carrying status " + std::to_string(status));
    }
  }
  const std::pair<pa::TimestampFailureV10, std::uint16_t> fatal[] = {
      {pa::TimestampFailureV10::decided_block_failed_range, 7},
      {pa::TimestampFailureV10::decided_block_failed_monotonicity, 8},
  };
  for (const auto& [failure, status] : fatal) {
    const auto subject = "status " + std::to_string(status);
    // `read_response` requires the kind to be 6: there is no argument that could
    // have made it anything else.
    const auto response =
        require_encoded(pa::encode_timestamp_failure_v10(11, failure),
                        pa::MessageKind::finalize_block, 11, subject);
    pv::require(response.status == status, subject + ": the wrong status");
  }
  for (const std::uint16_t status : {0, 6, 9}) {
    require_refused(pa::encode_timestamp_failure_v10(
                        11, static_cast<pa::TimestampFailureV10>(status)),
                    "a timestamp failure carrying status " + std::to_string(status));
  }
}

// The two responses that report the durable head, octet for octet: the stamp
// sits between the height and the root in both.
void check_head_layouts() {
  v10::Hash root{};
  root.fill(0xA5);
  constexpr std::uint64_t kStamp = 0x0102'0304'0506'0708ULL;
  Bytes info;
  append_u64(info, 10);
  append_u64(info, 5);
  append_u64(info, kStamp);
  info.insert(info.end(), root.begin(), root.end());
  pv::require(require_encoded(pa::encode_success_response_v10(
                                  pa::MessageKind::info, 1,
                                  pa::SuccessResponseV10{pa::ApplicationInfoV10{10, 5, kStamp, root}}),
                              pa::MessageKind::info, 1, "info")
                      .body == info,
              "info is not version, height, stamp, root");
  const Bytes commit(info.begin() + 8, info.end());
  pv::require(require_encoded(pa::encode_success_response_v10(
                                  pa::MessageKind::commit, 1,
                                  pa::SuccessResponseV10{pa::CommittedHeadV10{5, kStamp, root}}),
                              pa::MessageKind::commit, 1, "commit")
                      .body == commit,
              "commit is not height, stamp, root");
}

pa::EncodedFrameResult finalize_with(std::uint32_t code, Bytes receipt) {
  pa::FinalizedBlockV10 block;
  block.transaction_results.push_back(pa::TransactionResult{code, std::move(receipt)});
  return pa::encode_success_response_v10(pa::MessageKind::finalize_block, 1,
                                        pa::SuccessResponseV10{block});
}

// The encoder is the last place a disagreement between a declared code and its
// receipt can be caught, and under version ten the receipt's version is part of
// what the code is agreeing with.
void check_receipts() {
  v10::Receipt probe;
  probe.kind = 1;
  probe.result_code = static_cast<std::uint8_t>(v10::Result::unauthorized);
  const auto encoded = v10::encode_receipt(probe);
  pv::require(encoded.has_value(), "the probe receipt encodes");
  const auto code = pa::application_code(v10::Result::unauthorized);

  (void)require_encoded(finalize_with(code, *encoded), pa::MessageKind::finalize_block,
                        1, "a version-ten receipt beside its own code");
  auto stale = *encoded;
  stale[5] = 9;
  require_refused(finalize_with(code, stale), "a version-nine receipt");
  require_refused(finalize_with(pa::application_code(v10::Result::success), *encoded),
                  "a code that disagrees with its receipt");
  auto unknown = *encoded;
  unknown[39] = v10::kResultCodeCount;
  require_refused(finalize_with(256U + v10::kResultCodeCount, unknown),
                  "a receipt whose result byte names no result");
  // **The top of the range is written**, beside the refusal one past it. A
  // result of `49` is version ten's last, and its code is `305`.
  auto last = *encoded;
  last[39] = static_cast<std::uint8_t>(v10::Result::approval_lifetime_exceeded);
  (void)require_encoded(finalize_with(305, last), pa::MessageKind::finalize_block,
                        1, "a result of 49 under code 305");
  require_refused(finalize_with(304, last),
                  "a result of 49 under the code one below its own");
  require_refused(finalize_with(2, *encoded), "a refused admission carrying a receipt");

  // A mempool answer carrying a receipt would say the application executed
  // something to answer a question about a height nobody proposed.
  require_refused(pa::encode_success_response_v10(
                      pa::MessageKind::check_transaction, 1,
                      pa::SuccessResponseV10{pa::TransactionResult{0, *encoded}}),
                  "a mempool answer carrying a receipt");
  require_refused(pa::encode_success_response_v10(
                      pa::MessageKind::check_transaction, 1,
                      pa::SuccessResponseV10{pa::TransactionResult{4, {}}}),
                  "a mempool answer with an execution code");
}

// A response of the wrong type for its kind is refused rather than encoded as
// whatever happens to fit — and the decision, being one octet, would fit almost
// anywhere.
void check_wrong_types() {
  const pa::SuccessResponseV10 decision{pa::ProposalDecisionV10::accepted};
  for (const auto kind : kKinds) {
    if (kind == pa::MessageKind::process_proposal) continue;
    require_refused(pa::encode_success_response_v10(kind, 1, decision),
                    "a decision answering kind " +
                        std::to_string(static_cast<unsigned>(kind)));
  }
  require_refused(pa::encode_success_response_v10(
                      pa::MessageKind::process_proposal, 1,
                      pa::SuccessResponseV10{pa::CommittedHeadV10{}}),
                  "a committed head answering a proposal");
}

}  // namespace

void check_encoder() {
  check_decisions();
  check_statuses();
  check_head_layouts();
  check_receipts();
  check_wrong_types();
}

}  // namespace transport_v10_tests

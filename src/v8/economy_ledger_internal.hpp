#pragma once

// The value-movement helpers every transition shares, and the shared success
// tail.
//
// Each mutator returns `false` for an arithmetic or accounting outcome no
// conforming sequence produces — a debit below zero, a monetary value leaving
// `u64`, a channel issuing more than it accrued, issuance past the supply limit.
// That is an invariant failure rather than a transaction result, so it travels
// as a `nullopt` `Outcome` and rejects the whole block, exactly as
// `ledger-transition-v1` directs.

#include "protocol/v8/ledger.hpp"

namespace protocol::v8::internal {

std::uint64_t balance_of(const Ledger& ledger, const Octets32& escrow);
std::uint64_t nonce_of(const Ledger& ledger, const Octets32& escrow);
void set_nonce(Ledger& ledger, const Octets32& escrow, std::uint64_t nonce);

[[nodiscard]] bool credit(Ledger& ledger, const Octets32& escrow,
                          std::uint64_t amount);
[[nodiscard]] bool debit(Ledger& ledger, const Octets32& escrow,
                         std::uint64_t amount);
// The fixed fee the constitution applies to every accepted state transition.
[[nodiscard]] bool collect_fee(Ledger& ledger, const Octets32& escrow);
// Move value from a channel's outstanding into its issued total. Channel 8 has
// no accrual step, so it issues without an outstanding term.
[[nodiscard]] bool issue(Ledger& ledger, std::uint8_t channel,
                         std::uint64_t amount);
// `CHANNEL_CAP`'s predicate, over the accepted manifest's cap.
bool fits_channel(const Ledger& ledger, std::uint8_t channel,
                  std::uint64_t amount);

// The shared success tail: advance the escrow's nonce and take the fixed fee.
// Version one's rule applied to the escrow rather than to a key, so two signers
// acting concurrently on one escrow race for one sequence and the loser receives
// `NONCE_MISMATCH` with no new machinery.
std::optional<Outcome> charged(Ledger& ledger, const Octets32& escrow);

// The four beneficiary kinds the institutional legs credit, and the singleton
// beneficiary identifier every one of them uses.
std::optional<std::uint8_t> leg_beneficiary_kind(std::uint8_t channel_index);
inline constexpr Octets32 kSingletonBeneficiaryId{};

// The two transitions version eight adds, and the two block steps that write
// the same entries without any transaction asking for them.
//
// Each transition is stated as its ordered rejection conditions and its writes,
// over exactly the state it reads. **Version seven's shared envelope checks are
// not restated in them**: the nonce, the fee limit, the expiry, and the
// resolution of the acting escrow run before any of these conditions.
std::optional<Outcome> submit_response(Ledger& ledger, const Body& body,
                                       const Octets32& escrow);
std::optional<Outcome> file_dispute(Ledger& ledger, const Envelope& envelope,
                                    const Body& body, const Octets32& escrow,
                                    const SignatureVerifier& verify);

// The issue step's per-seat effect. A height is written once, and a second write
// to the same key is an invariant failure rather than a transaction result,
// because no conforming block issues twice.
[[nodiscard]] bool issue_challenge(Ledger& ledger, std::uint64_t challenge_height,
                                   std::uint32_t seat_id);
// The expiry step's per-entry effect, which no transaction can request. An
// answered challenge is deleted and nothing else is written; an outstanding one
// clears the seat's bit for the slot of its *challenge* height, creating the
// window record if it is absent. `true` when a slot was lost.
[[nodiscard]] bool expire_challenge(Ledger& ledger,
                                    std::uint64_t challenge_height,
                                    std::uint32_t seat_id, bool& lost);

// The six invariants version eight adds, on their own.
//
// A quiet height runs these and not the whole conservation gate, and the split
// is a cost decision rather than a weakening: the issue step and the expiry step
// are the only things that can execute at such a height, and the six below are
// exactly what they can break. The full gate walks every seat's assignment
// records once per seat, which ADR 0055 accepts at a block and which 1.35
// million quiet heights would not survive.
std::vector<std::string_view> uptime_failures(const Ledger& ledger);

// The seat window record for one window and seat, with an absent record read as
// a fully credited seat. `nullopt` is a record that will not decode, which is an
// invariant failure: every record in state was written by this kernel.
std::optional<SeatWindowRecord> window_record(const Ledger& ledger,
                                              std::uint64_t cycle_window,
                                              std::uint32_t seat_id);

// All sixteen kinds. Six write authority and identity; eight move or issue
// value; two carry uptime evidence.
std::optional<Outcome> dispatch(Ledger& ledger, const Envelope& envelope,
                                const Body& body, const Octets32* escrow,
                                const SignatureVerifier& verify);
// The eight kinds that move or issue value: the two transfers, the four seat
// transitions, the referral mint, the verified-user mint, and the refused direct
// issue.
std::optional<Outcome> dispatch_value(Ledger& ledger, const Envelope& envelope,
                                      const Body& body, const Octets32& escrow,
                                      const SignatureVerifier& verify);

// The three admission-side helpers the transitions share.
bool verify_hub_signature(const Ledger& ledger, const Octets32& identity,
                          std::span<const std::uint8_t> message,
                          const Bytes& signature, const SignatureVerifier& verify);
// The confirmation field of an operation that requires none must be 64 zero
// octets. Refused at execution with `UNAUTHORIZED`, for the two reasons ADR 0045
// records: admission cannot read the posture the predicate needs, and the
// result-code space has no `MALFORMED_TRANSACTION`.
bool confirmation_field_is_absent(const Bytes& field);
bool confirmation_required(const Ledger& ledger, const Octets32& escrow,
                           std::uint64_t amount);

}  // namespace protocol::v8::internal

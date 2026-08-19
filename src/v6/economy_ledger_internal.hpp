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

#include "protocol/v6/ledger.hpp"

namespace protocol::v6::internal {

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

// Kinds 1, 6, 10, 13, 14, 15, 16, 17, 18, and 19. The four seat transitions —
// purchase, activate, and the two mints that read a cycle assignment — are the
// next slice, and dispatch refuses a kind it does not yet run rather than
// silently succeeding.
std::optional<Outcome> dispatch(Ledger& ledger, const Envelope& envelope,
                                const Body& body, const Octets32* escrow,
                                const SignatureVerifier& verify);
// The four kinds that move or issue value: the two transfers, the verified-user
// mint, and the refused direct issue.
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

}  // namespace protocol::v6::internal

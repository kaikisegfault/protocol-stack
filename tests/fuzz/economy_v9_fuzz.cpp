// The version-nine decoders over arbitrary bytes.
//
// Twelve entry points take untrusted input — the signed transaction, the
// receipt, the genesis, the cycle assignment record, the recovery pool record,
// the two uptime values version eight added, the widened unreferred pool, and
// the four settlement values version nine adds — and all twelve are total: they
// answer `nullopt` rather than throwing, reading out of bounds, or depending on
// how the bytes were produced.
//
// What this asserts beyond "does not crash" is the two properties consensus
// rests on. **Decoding is deterministic**, so two nodes handed identical bytes
// reach identical answers. And **decoding round-trips**, so anything the
// decoder accepts re-encodes to exactly the bytes it came from — which is what
// makes a canonical encoding canonical, and what would catch a decoder that
// quietly tolerated a second representation of one transaction.
//
// This replaces `economy_v8_fuzz.cpp`, deleted with the rest of the
// version-eight stack (ADR 0092). The six inherited entry points are its harness
// with the namespace rebound. The six that are new are version nine's own
// surface, and **the zero rule is the one that most needs this**: a monthly
// figure or claim of zero is absence, so a decoder that opened one would give
// one fact two encodings, and no encoder can produce the witness.

#include "protocol/v9/economy.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <span>
#include <vector>

namespace v9 = protocol::v9;

namespace {

void require(bool condition) {
  if (!condition) std::abort();
}

template <typename Encoded>
void require_same_bytes(const Encoded& encoded,
                        std::span<const std::uint8_t> input) {
  require(encoded.size() == input.size());
  require(std::equal(encoded.begin(), encoded.end(), input.begin()));
}

void fuzz_transaction(std::span<const std::uint8_t> input) {
  const auto first = v9::decode_signed(input);
  const auto second = v9::decode_signed(input);
  require(first.has_value() == second.has_value());
  if (!first) return;

  const auto& left = first->envelope;
  const auto& right = second->envelope;
  require(left.kind == right.kind && left.chain_id == right.chain_id &&
          left.scheme == right.scheme &&
          left.authority_public_key == right.authority_public_key &&
          left.nonce == right.nonce && left.body == right.body &&
          left.fee_limit == right.fee_limit &&
          left.valid_until_height == right.valid_until_height &&
          first->signature == second->signature);

  // Anything admitted re-encodes to the exact bytes it came from. A decoder
  // that accepted a second representation of one transaction would fail here
  // rather than in whatever later step first noticed two transaction IDs for
  // one effect.
  require_same_bytes(v9::encode_signed(left, first->signature), input);

  // The kind the byte names governs every width, and the scheme is the one its
  // kind permits rather than whatever the header carried. Kind 22 is reached
  // here like every other kind, and is held to kind 4's widths by the codec's
  // own tables rather than by a special case.
  require(v9::is_transaction_kind(left.kind));
  require(left.body.size() == *v9::body_bytes(left.kind));
  require(input.size() == *v9::signed_bytes(left.kind));
  require(left.scheme == *v9::kind_scheme(left.kind));
  require(!v9::is_retired_kind(left.kind));

  // A registration has no escrow, so it has no sequence to advance and nothing
  // to charge; both fields are required to be zero rather than merely ignored.
  if (left.kind == static_cast<std::uint8_t>(v9::Kind::hub_register)) {
    require(left.nonce == 0 && left.fee_limit == 0);
  }

  // The signing message and the transaction identifier are functions of the
  // bytes, so they are stable over a decode that produced identical fields.
  require(v9::signing_message(v9::encode_unsigned(left)) ==
          v9::signing_message(v9::encode_unsigned(right)));
  require(v9::transaction_id(input) ==
          v9::transaction_id(v9::encode_signed(left, first->signature)));
}

void fuzz_receipt(std::span<const std::uint8_t> input) {
  const auto decoded = v9::decode_receipt(input);
  require(decoded.has_value() == v9::decode_receipt(input).has_value());
  if (!decoded) return;
  require(v9::receipt_is_consistent(*decoded));
  const auto reencoded = v9::encode_receipt(*decoded);
  require(reencoded.has_value());
  require_same_bytes(*reencoded, input);
}

// The decoder checks itself against the encoder, so what is asserted here is
// that the check holds from outside too, and that nothing it accepts carries a
// stamp C1 would refuse: a chain identity is a hash of these bytes, so a
// genesis outside the range would name a chain no node could start.
void fuzz_genesis(std::span<const std::uint8_t> input) {
  const auto decoded = v9::decode_genesis(input);
  require(decoded.has_value() == v9::decode_genesis(input).has_value());
  if (!decoded) return;
  require(decoded->genesis_timestamp <= v9::kMaxTimestampMillis);
  const auto reencoded = v9::encode_genesis(*decoded);
  require(reencoded.has_value());
  require_same_bytes(*reencoded, input);
  require(v9::chain_id(*decoded).has_value());
}

void fuzz_cycle_assignment(std::span<const std::uint8_t> input) {
  const auto decoded = v9::decode_cycle_assignment_value(input);
  require(decoded.has_value() ==
          v9::decode_cycle_assignment_value(input).has_value());
  if (!decoded) return;
  // Both bitmap widths follow from the recorded bit count and neither carries a
  // length prefix, so a record whose length disagrees with its own count must
  // never have been accepted.
  const auto width = v9::bitmap_bytes(decoded->bitmap_bits);
  require(decoded->accrued_bitmap.size() == width);
  require(decoded->winner_bitmap.size() == width);
  const auto reencoded = v9::cycle_assignment_value(*decoded);
  require(reencoded.has_value());
  require_same_bytes(*reencoded, input);
}

// A fixed-width state value, so the interesting property is not the width check
// but that a decoder handed forty arbitrary octets always produces five legs
// that re-encode to exactly those octets — a leg read at the wrong offset would
// round-trip to different bytes.
void fuzz_recovery_pool(std::span<const std::uint8_t> input) {
  const auto decoded = v9::decode_recovery_pool_value(input);
  require(decoded.has_value() ==
          v9::decode_recovery_pool_value(input).has_value());
  if (!decoded) return;
  require_same_bytes(v9::recovery_pool_value(*decoded), input);
}

// One octet wide and two-valued, so almost every input is refused. What this
// asserts is that the refusal is the *stated* one: anything accepted is `0` or
// `1`, and re-encoding it reproduces the octet.
void fuzz_open_challenge(std::span<const std::uint8_t> input) {
  const auto decoded = v9::decode_open_challenge_value(input);
  require(decoded.has_value() ==
          v9::decode_open_challenge_value(input).has_value());
  if (!decoded) return;
  require(*decoded == v9::kChallengeOutstanding ||
          *decoded == v9::kChallengeAnswered);
  const auto reencoded = v9::open_challenge_value(*decoded);
  require(reencoded.has_value());
  require_same_bytes(*reencoded, input);
}

// Both bitmaps are 24 bits in the low bits of a `u32` and the upper eight are
// pad the decoder refuses, so the encoder cannot emit a violating record and
// only arbitrary bytes can reach the rule. Anything accepted must satisfy both
// stated conditions — clear pad, and `disputed` a subset of `credited` — and
// re-encode to the octets it came from.
void fuzz_seat_window(std::span<const std::uint8_t> input) {
  const auto decoded = v9::decode_seat_window_value(input);
  require(decoded.has_value() ==
          v9::decode_seat_window_value(input).has_value());
  if (!decoded) return;
  require((decoded->credited & ~v9::kSlotBitmapMask) == 0);
  require((decoded->disputed & ~v9::kSlotBitmapMask) == 0);
  require((decoded->disputed & ~decoded->credited) == 0);
  require(v9::credited_slots(*decoded) <= v9::kSlotsPerWindow);
  const auto reencoded = v9::seat_window_value(*decoded);
  require(reencoded.has_value());
  require_same_bytes(*reencoded, input);
}

// Twenty-four octets carrying two identities over one entry: nothing is payable
// that was never accrued, and nothing is minted that was never assigned. The
// encoder refuses both, so only arbitrary bytes reach the decoder's copy.
void fuzz_unreferred_pool(std::span<const std::uint8_t> input) {
  const auto decoded = v9::decode_unreferred_pool_value(input);
  require(decoded.has_value() ==
          v9::decode_unreferred_pool_value(input).has_value());
  if (!decoded) return;
  require(decoded->payable_atomic <= decoded->accrued_atomic);
  require(decoded->minted_atomic <=
          decoded->accrued_atomic - decoded->payable_atomic);
  const auto reencoded = v9::unreferred_pool_value(*decoded);
  require(reencoded.has_value());
  require_same_bytes(*reencoded, input);
}

// The two month-valued entries share one bound and neither has an absence
// rule, because month zero is January 1970 and a real month.
void fuzz_months(std::span<const std::uint8_t> input) {
  const auto window = v9::decode_window_month_value(input);
  require(window.has_value() == v9::decode_window_month_value(input).has_value());
  if (window) {
    require(*window <= v9::kMaxMonthIndex);
    const auto reencoded = v9::window_month_value(*window);
    require(reencoded.has_value());
    require_same_bytes(*reencoded, input);
  }
  const auto cursor = v9::decode_settlement_cursor_value(input);
  require(cursor.has_value() ==
          v9::decode_settlement_cursor_value(input).has_value());
  if (cursor) {
    require(*cursor <= v9::kMaxMonthIndex);
    const auto reencoded = v9::settlement_cursor_value(*cursor);
    require(reencoded.has_value());
    require_same_bytes(*reencoded, input);
  }
}

// The two values whose zero is absence. A decoder that opened a zero would make
// "no entry" and "an entry holding nothing" two encodings of one fact, and the
// encoder refuses to write one, so this is the only place the rule is reached.
void fuzz_monthly_settlement(std::span<const std::uint8_t> input) {
  const auto figure = v9::decode_monthly_figure_value(input);
  require(figure.has_value() ==
          v9::decode_monthly_figure_value(input).has_value());
  if (figure) {
    require(*figure != 0);
    const auto reencoded = v9::monthly_figure_value(*figure);
    require(reencoded.has_value());
    require_same_bytes(*reencoded, input);
  }
  const auto claim = v9::decode_monthly_claim_value(input);
  require(claim.has_value() == v9::decode_monthly_claim_value(input).has_value());
  if (claim) {
    require(claim->accrued_atomic != 0);
    require(claim->minted_atomic <= claim->accrued_atomic);
    const auto reencoded = v9::monthly_claim_value(*claim);
    require(reencoded.has_value());
    require_same_bytes(*reencoded, input);
  }
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data,
                                      std::size_t size) {
  const std::span<const std::uint8_t> input{data, size};
  fuzz_transaction(input);
  fuzz_receipt(input);
  fuzz_genesis(input);
  fuzz_cycle_assignment(input);
  fuzz_recovery_pool(input);
  fuzz_open_challenge(input);
  fuzz_seat_window(input);
  fuzz_unreferred_pool(input);
  fuzz_months(input);
  fuzz_monthly_settlement(input);
  return 0;
}

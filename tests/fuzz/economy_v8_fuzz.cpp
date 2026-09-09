// The version-eight decoders over arbitrary bytes.
//
// Six entry points take untrusted input — the signed transaction, the receipt,
// the cycle assignment record, the recovery pool record, and the two uptime
// values version eight adds — and all six are total: they answer `nullopt`
// rather than throwing, reading out of bounds, or depending on how the bytes
// were produced.
//
// What this asserts beyond "does not crash" is the two properties consensus
// rests on. **Decoding is deterministic**, so two nodes handed identical bytes
// reach identical answers. And **decoding round-trips**, so anything the
// decoder accepts re-encodes to exactly the bytes it came from — which is what
// makes a canonical encoding canonical, and what would catch a decoder that
// quietly tolerated a second representation of one transaction.
//
// This replaces `economy_v7_fuzz.cpp`, deleted with the rest of the
// version-seven stack by ADR 0065's step 7. The four inherited entry points are
// its harness with the namespace rebound; the two uptime values are new, and
// the seat window record is the one that most needs this, because its pad rule
// is a refusal the encoder can never produce a witness for.

#include "protocol/v8/economy.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <span>
#include <vector>

namespace v8 = protocol::v8;

namespace {

void require(bool condition) {
  if (!condition) std::abort();
}

void fuzz_transaction(std::span<const std::uint8_t> input) {
  const auto first = v8::decode_signed(input);
  const auto second = v8::decode_signed(input);
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
  const auto reencoded = v8::encode_signed(left, first->signature);
  require(reencoded.size() == input.size());
  require(std::equal(reencoded.begin(), reencoded.end(), input.begin()));

  // The kind the byte names governs every width, and the scheme is the one its
  // kind permits rather than whatever the header carried.
  require(v8::is_transaction_kind(left.kind));
  require(left.body.size() == *v8::body_bytes(left.kind));
  require(input.size() == *v8::signed_bytes(left.kind));
  require(left.scheme == *v8::kind_scheme(left.kind));
  require(!v8::is_retired_kind(left.kind));

  // A registration has no escrow, so it has no sequence to advance and nothing
  // to charge; both fields are required to be zero rather than merely ignored.
  if (left.kind == static_cast<std::uint8_t>(v8::Kind::hub_register)) {
    require(left.nonce == 0 && left.fee_limit == 0);
  }

  // The signing message and the transaction identifier are functions of the
  // bytes, so they are stable over a decode that produced identical fields.
  require(v8::signing_message(v8::encode_unsigned(left)) ==
          v8::signing_message(v8::encode_unsigned(right)));
  require(v8::transaction_id(input) == v8::transaction_id(reencoded));
}

void fuzz_receipt(std::span<const std::uint8_t> input) {
  const auto decoded = v8::decode_receipt(input);
  require(decoded.has_value() == v8::decode_receipt(input).has_value());
  if (!decoded) return;
  require(v8::receipt_is_consistent(*decoded));
  const auto reencoded = v8::encode_receipt(*decoded);
  require(reencoded.has_value());
  require(reencoded->size() == input.size());
  require(std::equal(reencoded->begin(), reencoded->end(), input.begin()));
}

void fuzz_cycle_assignment(std::span<const std::uint8_t> input) {
  const auto decoded = v8::decode_cycle_assignment_value(input);
  require(decoded.has_value() ==
          v8::decode_cycle_assignment_value(input).has_value());
  if (!decoded) return;
  // Both bitmap widths follow from the recorded bit count and neither carries a
  // length prefix, so a record whose length disagrees with its own count must
  // never have been accepted.
  const auto width = v8::bitmap_bytes(decoded->bitmap_bits);
  require(decoded->accrued_bitmap.size() == width);
  require(decoded->winner_bitmap.size() == width);
  const auto reencoded = v8::cycle_assignment_value(*decoded);
  require(reencoded.has_value());
  require(reencoded->size() == input.size());
  require(std::equal(reencoded->begin(), reencoded->end(), input.begin()));
}

// A fixed-width state value, so the interesting property is not the width check
// but that a decoder handed forty arbitrary octets always produces five legs
// that re-encode to exactly those octets — a leg read at the wrong offset would
// round-trip to different bytes.
void fuzz_recovery_pool(std::span<const std::uint8_t> input) {
  const auto decoded = v8::decode_recovery_pool_value(input);
  require(decoded.has_value() ==
          v8::decode_recovery_pool_value(input).has_value());
  if (!decoded) return;
  const auto reencoded = v8::recovery_pool_value(*decoded);
  require(reencoded.size() == input.size());
  require(std::equal(reencoded.begin(), reencoded.end(), input.begin()));
}

// One octet wide and two-valued, so almost every input is refused. What this
// asserts is that the refusal is the *stated* one: anything accepted is `0` or
// `1`, and re-encoding it reproduces the octet.
void fuzz_open_challenge(std::span<const std::uint8_t> input) {
  const auto decoded = v8::decode_open_challenge_value(input);
  require(decoded.has_value() ==
          v8::decode_open_challenge_value(input).has_value());
  if (!decoded) return;
  require(*decoded == v8::kChallengeOutstanding ||
          *decoded == v8::kChallengeAnswered);
  const auto reencoded = v8::open_challenge_value(*decoded);
  require(reencoded.has_value());
  require(reencoded->size() == input.size());
  require(std::equal(reencoded->begin(), reencoded->end(), input.begin()));
}

// The record whose refusals no encoder can produce a witness for. Both bitmaps
// are 24 bits in the low bits of a `u32` and the upper eight are pad the
// decoder refuses, so the encoder cannot emit a violating record and only
// arbitrary bytes can reach the rule. Anything accepted must therefore satisfy
// both stated conditions — clear pad, and `disputed` a subset of `credited` —
// and re-encode to the octets it came from.
void fuzz_seat_window(std::span<const std::uint8_t> input) {
  const auto decoded = v8::decode_seat_window_value(input);
  require(decoded.has_value() ==
          v8::decode_seat_window_value(input).has_value());
  if (!decoded) return;
  require((decoded->credited & ~v8::kSlotBitmapMask) == 0);
  require((decoded->disputed & ~v8::kSlotBitmapMask) == 0);
  require((decoded->disputed & ~decoded->credited) == 0);
  // The credit the invariants read is derived from the two bitmaps rather than
  // stored, so it can never exceed what the evidence recorded. The bound is the
  // contract's own constant, which the containment vectors pin independently:
  // a maximal six-slot dispute records 64,800 seconds, so a window of any width
  // but twenty-four fails them.
  require(v8::credited_slots(*decoded) <= v8::kSlotsPerWindow);
  const auto reencoded = v8::seat_window_value(*decoded);
  require(reencoded.has_value());
  require(reencoded->size() == input.size());
  require(std::equal(reencoded->begin(), reencoded->end(), input.begin()));
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data,
                                      std::size_t size) {
  const std::span<const std::uint8_t> input{data, size};
  fuzz_transaction(input);
  fuzz_receipt(input);
  fuzz_cycle_assignment(input);
  fuzz_recovery_pool(input);
  fuzz_open_challenge(input);
  fuzz_seat_window(input);
  return 0;
}

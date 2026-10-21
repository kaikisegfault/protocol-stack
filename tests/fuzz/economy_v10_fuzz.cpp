// The version-ten decoders over arbitrary bytes.
//
// Sixteen entry points take untrusted input — version nine's twelve, rebound,
// and the four registry values version ten adds — and all sixteen are total:
// they answer `nullopt` rather than throwing, reading out of bounds, or
// depending on how the bytes were produced.
//
// What this asserts beyond "does not crash" is the two properties consensus
// rests on. **Decoding is deterministic**, so two nodes handed identical bytes
// reach identical answers. And **decoding round-trips**, so anything the
// decoder accepts re-encodes to exactly the bytes it came from — which is what
// makes a canonical encoding canonical, and what would catch a decoder that
// quietly tolerated a second representation of one transaction.
//
// This is `economy_v9_fuzz.cpp`'s counterpart, which ADR 0104's last step must
// keep when version nine's stack is deleted. Version nine's twelve entry points
// are its harness with the namespace rebound. The rest is version ten's own
// surface:
//
// - **the founder count's zero rule**: a count of zero is absence, so a decoder
//   that opened one would give one fact two encodings, and no encoder can
//   produce the witness (ADR 0107);
// - a machine key written at height zero and a retirement at height zero, the
//   other two values no transition writes;
// - **the approval over whatever decodes**: an approval message exists exactly
//   for the body-carried kinds, its approved bytes differ from the unsigned
//   encoding in the HUB field alone, and the lifetime rule never wraps at the
//   top of the height range.

#include "protocol/v10/economy.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <limits>
#include <span>
#include <vector>

namespace v10 = protocol::v10;

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

// Version ten's single approval message, checked over every transaction that
// decodes. The approved bytes are the unsigned encoding with the HUB field set
// to zero, so they must have the unsigned encoding's length, agree with it
// everywhere outside one 64-octet run, and hold zeros inside it.
void check_approval(const v10::Envelope& envelope) {
  const auto approved = v10::approved_bytes(envelope);
  const auto message = v10::approval_message(envelope);
  require(approved.has_value() == v10::is_approval_kind(envelope.kind));
  require(message.has_value() == approved.has_value());
  if (approved) {
    const auto unsigned_bytes = v10::encode_unsigned(envelope);
    require(approved->size() == unsigned_bytes.size());
    std::size_t differing = 0;
    for (std::size_t index = 0; index < approved->size(); ++index) {
      if ((*approved)[index] != unsigned_bytes[index]) {
        require((*approved)[index] == 0);
        ++differing;
      }
    }
    require(differing <= v10::kSignatureBytes);
    require(message->size() > approved->size());
    require(std::equal(approved->begin(), approved->end(),
                       message->end() - static_cast<std::ptrdiff_t>(approved->size())));
  }

  // A transaction with no HUB proof is never governed, whatever its validity.
  // One that carries a proof is governed exactly when its validity reaches more
  // than one slot past the height, including at the top of the `u64` range,
  // where a sum would wrap and admit everything.
  const auto top = std::numeric_limits<std::uint64_t>::max();
  for (const std::uint64_t height :
       {std::uint64_t{0}, envelope.valid_until_height, top - 1, top}) {
    const bool exceeded = v10::approval_lifetime_exceeded(envelope, height);
    if (!v10::carries_hub_proof(envelope)) {
      require(!exceeded);
      continue;
    }
    const bool beyond = envelope.valid_until_height > height &&
                        envelope.valid_until_height - height >
                            v10::kApprovalLifetimeBlocks;
    require(exceeded == beyond);
  }
  if (v10::is_always_proven_kind(envelope.kind)) {
    require(v10::carries_hub_proof(envelope));
  }
}

void fuzz_transaction(std::span<const std::uint8_t> input) {
  const auto first = v10::decode_signed(input);
  const auto second = v10::decode_signed(input);
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
  require_same_bytes(v10::encode_signed(left, first->signature), input);

  // The kind the byte names governs every width, and the scheme is the one its
  // kind permits rather than whatever the header carried. Kind 10's wider body
  // and kind 23 are reached here like every other kind, held to their widths by
  // the codec's own tables rather than by a special case.
  require(v10::is_transaction_kind(left.kind));
  require(left.body.size() == *v10::body_bytes(left.kind));
  require(input.size() == *v10::signed_bytes(left.kind));
  require(left.scheme == *v10::kind_scheme(left.kind));
  require(!v10::is_retired_kind(left.kind));

  // A registration has no escrow, so it has no sequence to advance and nothing
  // to charge; both fields are required to be zero rather than merely ignored.
  if (left.kind == static_cast<std::uint8_t>(v10::Kind::hub_register)) {
    require(left.nonce == 0 && left.fee_limit == 0);
  }

  // The signing message and the transaction identifier are functions of the
  // bytes, so they are stable over a decode that produced identical fields.
  require(v10::signing_message(v10::encode_unsigned(left)) ==
          v10::signing_message(v10::encode_unsigned(right)));
  require(v10::transaction_id(input) ==
          v10::transaction_id(v10::encode_signed(left, first->signature)));

  check_approval(left);
}

void fuzz_receipt(std::span<const std::uint8_t> input) {
  const auto decoded = v10::decode_receipt(input);
  require(decoded.has_value() == v10::decode_receipt(input).has_value());
  if (!decoded) return;
  require(v10::receipt_is_consistent(*decoded));
  const auto reencoded = v10::encode_receipt(*decoded);
  require(reencoded.has_value());
  require_same_bytes(*reencoded, input);
}

// The decoder checks itself against the encoder, so what is asserted here is
// that the check holds from outside too, and that nothing it accepts carries a
// stamp C1 would refuse: a chain identity is a hash of these bytes, so a
// genesis outside the range would name a chain no node could start.
void fuzz_genesis(std::span<const std::uint8_t> input) {
  const auto decoded = v10::decode_genesis(input);
  require(decoded.has_value() == v10::decode_genesis(input).has_value());
  if (!decoded) return;
  require(decoded->genesis_timestamp <= v10::kMaxTimestampMillis);
  const auto reencoded = v10::encode_genesis(*decoded);
  require(reencoded.has_value());
  require_same_bytes(*reencoded, input);
  require(v10::chain_id(*decoded).has_value());
}

void fuzz_cycle_assignment(std::span<const std::uint8_t> input) {
  const auto decoded = v10::decode_cycle_assignment_value(input);
  require(decoded.has_value() ==
          v10::decode_cycle_assignment_value(input).has_value());
  if (!decoded) return;
  // Both bitmap widths follow from the recorded bit count and neither carries a
  // length prefix, so a record whose length disagrees with its own count must
  // never have been accepted.
  const auto width = v10::bitmap_bytes(decoded->bitmap_bits);
  require(decoded->accrued_bitmap.size() == width);
  require(decoded->winner_bitmap.size() == width);
  const auto reencoded = v10::cycle_assignment_value(*decoded);
  require(reencoded.has_value());
  require_same_bytes(*reencoded, input);
}

// A fixed-width state value, so the interesting property is not the width check
// but that a decoder handed forty arbitrary octets always produces five legs
// that re-encode to exactly those octets — a leg read at the wrong offset would
// round-trip to different bytes.
void fuzz_recovery_pool(std::span<const std::uint8_t> input) {
  const auto decoded = v10::decode_recovery_pool_value(input);
  require(decoded.has_value() ==
          v10::decode_recovery_pool_value(input).has_value());
  if (!decoded) return;
  require_same_bytes(v10::recovery_pool_value(*decoded), input);
}

// One octet wide and two-valued, so almost every input is refused. What this
// asserts is that the refusal is the *stated* one: anything accepted is `0` or
// `1`, and re-encoding it reproduces the octet.
void fuzz_open_challenge(std::span<const std::uint8_t> input) {
  const auto decoded = v10::decode_open_challenge_value(input);
  require(decoded.has_value() ==
          v10::decode_open_challenge_value(input).has_value());
  if (!decoded) return;
  require(*decoded == v10::kChallengeOutstanding ||
          *decoded == v10::kChallengeAnswered);
  const auto reencoded = v10::open_challenge_value(*decoded);
  require(reencoded.has_value());
  require_same_bytes(*reencoded, input);
}

// Both bitmaps are 24 bits in the low bits of a `u32` and the upper eight are
// pad the decoder refuses, so the encoder cannot emit a violating record and
// only arbitrary bytes can reach the rule. Anything accepted must satisfy both
// stated conditions — clear pad, and `disputed` a subset of `credited` — and
// re-encode to the octets it came from.
void fuzz_seat_window(std::span<const std::uint8_t> input) {
  const auto decoded = v10::decode_seat_window_value(input);
  require(decoded.has_value() ==
          v10::decode_seat_window_value(input).has_value());
  if (!decoded) return;
  require((decoded->credited & ~v10::kSlotBitmapMask) == 0);
  require((decoded->disputed & ~v10::kSlotBitmapMask) == 0);
  require((decoded->disputed & ~decoded->credited) == 0);
  require(v10::credited_slots(*decoded) <= v10::kSlotsPerWindow);
  const auto reencoded = v10::seat_window_value(*decoded);
  require(reencoded.has_value());
  require_same_bytes(*reencoded, input);
}

// Twenty-four octets carrying two identities over one entry: nothing is payable
// that was never accrued, and nothing is minted that was never assigned. The
// encoder refuses both, so only arbitrary bytes reach the decoder's copy.
void fuzz_unreferred_pool(std::span<const std::uint8_t> input) {
  const auto decoded = v10::decode_unreferred_pool_value(input);
  require(decoded.has_value() ==
          v10::decode_unreferred_pool_value(input).has_value());
  if (!decoded) return;
  require(decoded->payable_atomic <= decoded->accrued_atomic);
  require(decoded->minted_atomic <=
          decoded->accrued_atomic - decoded->payable_atomic);
  const auto reencoded = v10::unreferred_pool_value(*decoded);
  require(reencoded.has_value());
  require_same_bytes(*reencoded, input);
}

// The two month-valued entries share one bound and neither has an absence
// rule, because month zero is January 1970 and a real month.
void fuzz_months(std::span<const std::uint8_t> input) {
  const auto window = v10::decode_window_month_value(input);
  require(window.has_value() == v10::decode_window_month_value(input).has_value());
  if (window) {
    require(*window <= v10::kMaxMonthIndex);
    const auto reencoded = v10::window_month_value(*window);
    require(reencoded.has_value());
    require_same_bytes(*reencoded, input);
  }
  const auto cursor = v10::decode_settlement_cursor_value(input);
  require(cursor.has_value() ==
          v10::decode_settlement_cursor_value(input).has_value());
  if (cursor) {
    require(*cursor <= v10::kMaxMonthIndex);
    const auto reencoded = v10::settlement_cursor_value(*cursor);
    require(reencoded.has_value());
    require_same_bytes(*reencoded, input);
  }
}

// The two values whose zero is absence. A decoder that opened a zero would make
// "no entry" and "an entry holding nothing" two encodings of one fact, and the
// encoder refuses to write one, so this is the only place the rule is reached.
void fuzz_monthly_settlement(std::span<const std::uint8_t> input) {
  const auto figure = v10::decode_monthly_figure_value(input);
  require(figure.has_value() ==
          v10::decode_monthly_figure_value(input).has_value());
  if (figure) {
    require(*figure != 0);
    const auto reencoded = v10::monthly_figure_value(*figure);
    require(reencoded.has_value());
    require_same_bytes(*reencoded, input);
  }
  const auto claim = v10::decode_monthly_claim_value(input);
  require(claim.has_value() == v10::decode_monthly_claim_value(input).has_value());
  if (claim) {
    require(claim->accrued_atomic != 0);
    require(claim->minted_atomic <= claim->accrued_atomic);
    const auto reencoded = v10::monthly_claim_value(*claim);
    require(reencoded.has_value());
    require_same_bytes(*reencoded, input);
  }
}

// Version ten's four registry values. The machine key and the retirement each
// refuse a height of zero, the owner value is any `u32`, and the founder count
// refuses zero and anything above the limit. Every rule is the encoder's, so
// arbitrary bytes are the only way to reach the decoder's copy of it.
void fuzz_registry(std::span<const std::uint8_t> input) {
  const auto key = v10::decode_machine_key_value(input);
  require(key.has_value() == v10::decode_machine_key_value(input).has_value());
  if (key) {
    require(key->registered_at_height != 0);
    const auto reencoded = v10::machine_key_value(*key);
    require(reencoded.has_value());
    require_same_bytes(*reencoded, input);
  }
  const auto retirement = v10::decode_launch_retirement_value(input);
  require(retirement.has_value() ==
          v10::decode_launch_retirement_value(input).has_value());
  if (retirement) {
    require(*retirement != 0);
    const auto reencoded = v10::launch_retirement_value(*retirement);
    require(reencoded.has_value());
    require_same_bytes(*reencoded, input);
  }
  const auto owner = v10::decode_machine_key_owner_value(input);
  require(owner.has_value() == v10::decode_machine_key_owner_value(input).has_value());
  if (owner) require_same_bytes(v10::machine_key_owner_value(*owner), input);
  const auto founder = v10::decode_founder_registrations_value(input);
  require(founder.has_value() ==
          v10::decode_founder_registrations_value(input).has_value());
  if (founder) {
    require(founder->registrations_in_window != 0);
    require(founder->registrations_in_window <=
            v10::kFounderRegistrationsPerWindow);
    const auto reencoded = v10::founder_registrations_value(*founder);
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
  fuzz_registry(input);
  return 0;
}

// The version-seven decoders over arbitrary bytes.
//
// Four entry points take untrusted input — the signed transaction, the receipt,
// the one variable-width state value, and the recovery pool record — and all
// four are total: they answer `nullopt` rather than throwing, reading out of
// bounds, or depending on how the bytes were produced.
//
// What this asserts beyond "does not crash" is the two properties consensus
// rests on. **Decoding is deterministic**, so two nodes handed identical bytes
// reach identical answers. And **decoding round-trips**, so anything the
// decoder accepts re-encodes to exactly the bytes it came from — which is what
// makes a canonical encoding canonical, and what would catch a decoder that
// quietly tolerated a second representation of one transaction.

#include "protocol/v7/economy.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <span>
#include <vector>

namespace v7 = protocol::v7;

namespace {

void require(bool condition) {
  if (!condition) std::abort();
}

void fuzz_transaction(std::span<const std::uint8_t> input) {
  const auto first = v7::decode_signed(input);
  const auto second = v7::decode_signed(input);
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
  const auto reencoded = v7::encode_signed(left, first->signature);
  require(reencoded.size() == input.size());
  require(std::equal(reencoded.begin(), reencoded.end(), input.begin()));

  // The kind the byte names governs every width, and the scheme is the one its
  // kind permits rather than whatever the header carried.
  require(v7::is_transaction_kind(left.kind));
  require(left.body.size() == *v7::body_bytes(left.kind));
  require(input.size() == *v7::signed_bytes(left.kind));
  require(left.scheme == *v7::kind_scheme(left.kind));
  require(!v7::is_retired_kind(left.kind));

  // A registration has no escrow, so it has no sequence to advance and nothing
  // to charge; both fields are required to be zero rather than merely ignored.
  if (left.kind == static_cast<std::uint8_t>(v7::Kind::hub_register)) {
    require(left.nonce == 0 && left.fee_limit == 0);
  }

  // The signing message and the transaction identifier are functions of the
  // bytes, so they are stable over a decode that produced identical fields.
  require(v7::signing_message(v7::encode_unsigned(left)) ==
          v7::signing_message(v7::encode_unsigned(right)));
  require(v7::transaction_id(input) == v7::transaction_id(reencoded));
}

void fuzz_receipt(std::span<const std::uint8_t> input) {
  const auto decoded = v7::decode_receipt(input);
  require(decoded.has_value() == v7::decode_receipt(input).has_value());
  if (!decoded) return;
  require(v7::receipt_is_consistent(*decoded));
  const auto reencoded = v7::encode_receipt(*decoded);
  require(reencoded.has_value());
  require(reencoded->size() == input.size());
  require(std::equal(reencoded->begin(), reencoded->end(), input.begin()));
}

void fuzz_cycle_assignment(std::span<const std::uint8_t> input) {
  const auto decoded = v7::decode_cycle_assignment_value(input);
  require(decoded.has_value() ==
          v7::decode_cycle_assignment_value(input).has_value());
  if (!decoded) return;
  // Both bitmap widths follow from the recorded bit count and neither carries a
  // length prefix, so a record whose length disagrees with its own count must
  // never have been accepted.
  const auto width = v7::bitmap_bytes(decoded->bitmap_bits);
  require(decoded->accrued_bitmap.size() == width);
  require(decoded->winner_bitmap.size() == width);
  const auto reencoded = v7::cycle_assignment_value(*decoded);
  require(reencoded.has_value());
  require(reencoded->size() == input.size());
  require(std::equal(reencoded->begin(), reencoded->end(), input.begin()));
}

// Version seven's own state value. It is fixed-width, so the interesting
// property is not the width check but that a decoder handed forty arbitrary
// octets always produces five legs that re-encode to exactly those octets —
// a leg read at the wrong offset would round-trip to different bytes.
void fuzz_recovery_pool(std::span<const std::uint8_t> input) {
  const auto decoded = v7::decode_recovery_pool_value(input);
  require(decoded.has_value() ==
          v7::decode_recovery_pool_value(input).has_value());
  if (!decoded) return;
  const auto reencoded = v7::recovery_pool_value(*decoded);
  require(reencoded.size() == input.size());
  require(std::equal(reencoded.begin(), reencoded.end(), input.begin()));
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data,
                                      std::size_t size) {
  const std::span<const std::uint8_t> input{data, size};
  fuzz_transaction(input);
  fuzz_receipt(input);
  fuzz_cycle_assignment(input);
  fuzz_recovery_pool(input);
  return 0;
}

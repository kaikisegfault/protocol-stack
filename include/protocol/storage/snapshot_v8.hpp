#pragma once

// The version-eight state snapshot: a whole `Ledger` as canonical bytes, and
// the restore that turns those bytes back into a ledger that keeps executing.
//
// **A snapshot is node-local.** It is consensus-visible only through the state
// root it must reproduce, which is why it follows ADR 0007's precedent — an ADR
// and an implementation with evidence, rather than a transition specification —
// and why it may be stricter than the kernel's own decoders without changing a
// single accepted state. ADR 0056 fixed the shape for version seven and ADR 0066
// records what version eight changes.
//
// The payload carries exactly what the state root commits to: the summary, the
// ordered account map, and the ordered economy map, in the shapes
// `protocol::v8::state_root` takes them. Encoding a second projection would
// create a second opinion about what a state *is*, and the root would then be
// checking the snapshot against itself.
//
// **The uptime carrier's two entry kinds ride in the economy section as entries
// rather than as typed records**, because `Ledger::uptime` is one raw
// key-to-value map holding every one of them. Decoding them into fields here
// would be a second encoding of the key space the two version-eight transitions
// write, with nothing keeping the two equal.
//
// `assigned_permissions` is deliberately **not** in the payload. It is not a
// state entry, so nothing in the root commits to it; the restore re-derives it
// from the assignment records, which commit to both of its terms.

#include "protocol/v8/ledger.hpp"

#include <cstdint>
#include <span>
#include <variant>

namespace protocol::storage {

// Ordered by where the restore gives up, which is also the order a reader
// should try to explain a failure in.
enum class SnapshotV8Error : std::uint8_t {
  malformed = 1,
  unsupported_version = 2,
  size_overflow = 3,
  digest_mismatch = 4,
  immutable_parameters_mismatch = 5,
  // An entry, an account, or an ordering no conforming transition could have
  // written. Failing here rather than at the root is what makes a tampered
  // field a parse error with a subject rather than a hash that does not match.
  invalid_state = 6,
  // Gate 1: the ledger rebuilt from the payload does not project to the root
  // the payload claims, so the reconstruction lost or invented something.
  state_root_mismatch = 7,
  // Gate 2: the payload's own entries do not produce the root it claims, so the
  // payload is inconsistent with itself whatever the rebuild did.
  payload_root_mismatch = 8,
  // Gate 3: the restored state is one no sequence of blocks could have reached.
  not_conserved = 9,
};

// The five figures a version-eight chain fixes at genesis and no transition
// changes. They are supplied out of band at restore for the reason version one
// supplies its own: a snapshot that could redefine them would be a snapshot that
// could move a node to a different chain.
//
// The verifier key is also an economy entry, so a payload carries it twice and
// the restore requires the two copies to agree.
//
// **The dispute authority key is version eight's addition and it has no second
// copy**, because it is a genesis field bound into the chain identity rather
// than a state entry. Nothing in the state root commits to it, so it is the one
// parameter a payload could otherwise redefine unnoticed — and whoever holds it
// can void a machine's uptime. Comparing it is what stops a restored node from
// answering to a different dispute authority than its peers.
struct SnapshotParametersV8 {
  protocol::v8::Octets32 chain_id{};
  std::uint64_t supply_limit = 0;
  std::uint64_t fixed_fee = 0;
  protocol::v8::Octets32 verifier_key{};
  protocol::v8::Octets32 dispute_authority_key{};

  bool operator==(const SnapshotParametersV8&) const = default;
};

SnapshotParametersV8 snapshot_parameters(const protocol::v8::Ledger& ledger);

struct EncodedSnapshotV8 {
  protocol::v8::Bytes payload;
  protocol::v8::Hash state_root;
  protocol::v8::Hash digest;

  bool operator==(const EncodedSnapshotV8&) const = default;
};

struct DecodedSnapshotV8 {
  protocol::v8::Ledger ledger;
  protocol::v8::Hash state_root;
  protocol::v8::Hash digest;
};

using SnapshotV8EncodeResult = std::variant<EncodedSnapshotV8, SnapshotV8Error>;
using SnapshotV8DecodeResult = std::variant<DecodedSnapshotV8, SnapshotV8Error>;

// `invalid_state` for a ledger that does not commit a root, which is a state no
// conforming block execution leaves behind.
SnapshotV8EncodeResult encode_snapshot_v8(const protocol::v8::Ledger& ledger);

// A restore hands back a state some sequence of blocks could have produced, or
// it hands back nothing.
SnapshotV8DecodeResult decode_snapshot_v8(
    std::span<const std::uint8_t> payload,
    const SnapshotParametersV8& expected_parameters);

}  // namespace protocol::storage

#pragma once

// The version-nine state snapshot: a whole `Ledger` as canonical bytes, and the
// restore that turns those bytes back into a ledger that keeps executing.
//
// **A snapshot is node-local.** It is consensus-visible only through the state
// root it must reproduce, which is why it follows ADR 0007's precedent — an ADR
// and an implementation with evidence, rather than a transition specification —
// and why it may be stricter than the kernel's own decoders without changing a
// single accepted state. ADR 0056 fixed the shape for version seven, ADR 0066
// recorded version eight's changes, and this version's are below.
//
// The payload carries exactly what the state root commits to: the summary, the
// ordered account map, and the ordered economy map, in the shapes
// `protocol::v9::state_root` takes them. Encoding a second projection would
// create a second opinion about what a state *is*, and the root would then be
// checking the snapshot against itself.
//
// **The head is two scalars under version nine and the payload carries both.**
// `Ledger::timestamp` is a field rather than a parameter because C2 compares a
// block's stamp with its predecessor's, so a machine that restored from a
// snapshot must hold it. A payload that round-tripped the height and dropped the
// stamp would restore a ledger whose next block commits a root naming a height
// the stamp does not belong to, and **every later block would still satisfy C2**
// because the stale stamp is smaller — a wrong root rather than a refusal, which
// is the direction that hides. The state root commits to it, so gates 1 and 2
// both catch it; the round-trip vector names it anyway, because a gate that
// happens to catch something is weaker evidence than a test that aims at it.
//
// **Version nine adds no snapshot parameter, and that is worth stating.** Its
// one new genesis field is the genesis timestamp, and a restored ledger does not
// need it: C2's genesis case applies only at height one, `Ledger` keeps no
// separate copy, and `chain_id` — which *is* compared — commits to the genesis
// bytes the value came from. The dispute authority key needed a parameter for
// the opposite reason: the ledger retains it, transitions read it, and no root
// commits to it.
//
// **The uptime carrier's two entry kinds ride in the economy section as entries
// rather than as typed records**, because `Ledger::uptime` is one raw
// key-to-value map holding every one of them. **The four kinds version nine adds
// do not**, because version nine holds them as typed fields — nothing in this
// version reads that raw key space, so the projection is where they become
// entries and this decoder is its inverse. Which side reads the key space is the
// whole of the difference; ADR 0078 records it.
//
// `assigned_permissions` is deliberately **not** in the payload. It is not a
// state entry, so nothing in the root commits to it; the restore re-derives it
// from the assignment records, which commit to both of its terms.

#include "protocol/v9/ledger.hpp"

#include <cstdint>
#include <span>
#include <variant>

namespace protocol::storage {

// Ordered by where the restore gives up, which is also the order a reader
// should try to explain a failure in.
enum class SnapshotV9Error : std::uint8_t {
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
  // Under version nine this gate also carries the clock: the kernel's invariants
  // check the timestamp's range, the window-month retention, the one-open-month
  // rule over the figures, and the two pool identities, so none of those needs a
  // second statement here.
  not_conserved = 9,
};

// The five figures a version-nine chain fixes at genesis and no transition
// changes. They are supplied out of band at restore for the reason version one
// supplies its own: a snapshot that could redefine them would be a snapshot that
// could move a node to a different chain.
//
// The verifier key is also an economy entry, so a payload carries it twice and
// the restore requires the two copies to agree.
//
// **The dispute authority key has no second copy**, because it is a genesis
// field bound into the chain identity rather than a state entry. Nothing in the
// state root commits to it, so it is the one parameter a payload could otherwise
// redefine unnoticed — and whoever holds it can void a machine's uptime.
// Comparing it is what stops a restored node from answering to a different
// dispute authority than its peers.
struct SnapshotParametersV9 {
  protocol::v9::Octets32 chain_id{};
  std::uint64_t supply_limit = 0;
  std::uint64_t fixed_fee = 0;
  protocol::v9::Octets32 verifier_key{};
  protocol::v9::Octets32 dispute_authority_key{};

  bool operator==(const SnapshotParametersV9&) const = default;
};

SnapshotParametersV9 snapshot_parameters(const protocol::v9::Ledger& ledger);

struct EncodedSnapshotV9 {
  protocol::v9::Bytes payload;
  protocol::v9::Hash state_root;
  protocol::v9::Hash digest;

  bool operator==(const EncodedSnapshotV9&) const = default;
};

struct DecodedSnapshotV9 {
  protocol::v9::Ledger ledger;
  protocol::v9::Hash state_root;
  protocol::v9::Hash digest;
};

using SnapshotV9EncodeResult = std::variant<EncodedSnapshotV9, SnapshotV9Error>;
using SnapshotV9DecodeResult = std::variant<DecodedSnapshotV9, SnapshotV9Error>;

// `invalid_state` for a ledger that does not commit a root, which is a state no
// conforming block execution leaves behind.
SnapshotV9EncodeResult encode_snapshot_v9(const protocol::v9::Ledger& ledger);

// A restore hands back a state some sequence of blocks could have produced, or
// it hands back nothing.
SnapshotV9DecodeResult decode_snapshot_v9(
    std::span<const std::uint8_t> payload,
    const SnapshotParametersV9& expected_parameters);

}  // namespace protocol::storage

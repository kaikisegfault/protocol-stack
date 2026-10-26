#pragma once

// The version-ten state snapshot: a whole `Ledger` as canonical bytes, and the
// restore that turns those bytes back into a ledger that keeps executing.
//
// **A snapshot is node-local.** It is consensus-visible only through the state
// root it must reproduce, which is why it follows ADR 0007's precedent — an ADR
// and an implementation with evidence, rather than a transition specification —
// and why it may be stricter than the kernel's own decoders without changing a
// single accepted state. ADR 0056 fixed the shape for version seven, ADR 0066
// and ADR 0080 recorded versions eight and nine, and ADR 0108 records this one.
//
// The payload carries exactly what the state root commits to: the summary, the
// ordered account map, and the ordered economy map, in the shapes
// `protocol::v10::state_root` takes them. Encoding a second projection would
// create a second opinion about what a state *is*, and the root would then be
// checking the snapshot against itself.
//
// **The head is version nine's two scalars**, the height and the timestamp,
// and the payload carries both at version nine's offsets. ADR 0080 records why
// the timestamp is a field a restore must not lose.
//
// **Version ten adds one snapshot parameter, the build authority key**, for the
// reason version eight added the dispute authority key: the ledger retains it,
// kind 23 reads it, and no root commits to it. A payload that could redefine it
// could move a restored node to a different build authority unnoticed, and
// whoever holds that key decides which machines may admit people. It rides in
// the prefix immediately after the dispute authority key, which is where
// genesis carries it.
//
// **The four entry kinds version ten adds are decoded into typed fields**, as
// version nine's four are, because version ten holds them as typed maps and
// nothing reads their raw key space. The machine keys, their inverse, the
// launch key's retirement, and the founder counts each go through the kernel's
// own value decoder, called rather than restated.
//
// **The registry's invariants are gate 3's, with one exception.** Version ten's
// `conservation_failures` carries invariants 1 to 6 and 8. The seventh says a
// retirement, once written, is never removed, and that is a statement about two
// heights where a snapshot holds one. So the restore checks what one height
// can show about the retirement instead (ADR 0108).
//
// `assigned_permissions` is deliberately **not** in the payload. It is not a
// state entry, so nothing in the root commits to it; the restore re-derives it
// from the assignment records, which commit to both of its terms.

#include "protocol/v10/ledger.hpp"

#include <cstdint>
#include <span>
#include <variant>

namespace protocol::storage {

// Ordered by where the restore gives up, which is also the order a reader
// should try to explain a failure in.
enum class SnapshotV10Error : std::uint8_t {
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
  // Under version ten this gate also carries the registry: the kernel's
  // invariants hold every machine key to an activated seat, the owner entries to
  // the exact inverse, every mark and every founder count to the head's window,
  // and every founder count to someone who owns a machine.
  not_conserved = 9,
};

// The six figures a version-ten chain fixes at genesis and no transition
// changes. They are supplied out of band at restore for the reason version one
// supplies its own: a snapshot that could redefine them would be a snapshot that
// could move a node to a different chain.
//
// The launch key is also an economy entry, kind 8, which keeps the name version
// six gave it. So a payload carries it twice and the restore requires the two
// copies to agree.
//
// **The dispute authority key and the build authority key have no second
// copy**, because each is a genesis field bound into the chain identity rather
// than a state entry. Nothing in the state root commits to either, so they are
// the two parameters a payload could otherwise redefine unnoticed. Whoever
// holds the first can void a machine's uptime, and whoever holds the second
// decides which machines may admit people. Comparing them is what stops a
// restored node from answering to a different authority than its peers.
struct SnapshotParametersV10 {
  protocol::v10::Octets32 chain_id{};
  std::uint64_t supply_limit = 0;
  std::uint64_t fixed_fee = 0;
  protocol::v10::Octets32 launch_key{};
  protocol::v10::Octets32 dispute_authority_key{};
  protocol::v10::Octets32 build_authority_key{};

  bool operator==(const SnapshotParametersV10&) const = default;
};

SnapshotParametersV10 snapshot_parameters(const protocol::v10::Ledger& ledger);

struct EncodedSnapshotV10 {
  protocol::v10::Bytes payload;
  protocol::v10::Hash state_root;
  protocol::v10::Hash digest;

  bool operator==(const EncodedSnapshotV10&) const = default;
};

struct DecodedSnapshotV10 {
  protocol::v10::Ledger ledger;
  protocol::v10::Hash state_root;
  protocol::v10::Hash digest;
};

using SnapshotV10EncodeResult = std::variant<EncodedSnapshotV10, SnapshotV10Error>;
using SnapshotV10DecodeResult = std::variant<DecodedSnapshotV10, SnapshotV10Error>;

// `invalid_state` for a ledger that does not commit a root, which is a state no
// conforming block execution leaves behind.
SnapshotV10EncodeResult encode_snapshot_v10(const protocol::v10::Ledger& ledger);

// A restore hands back a state some sequence of blocks could have produced, or
// it hands back nothing.
SnapshotV10DecodeResult decode_snapshot_v10(
    std::span<const std::uint8_t> payload,
    const SnapshotParametersV10& expected_parameters);

}  // namespace protocol::storage

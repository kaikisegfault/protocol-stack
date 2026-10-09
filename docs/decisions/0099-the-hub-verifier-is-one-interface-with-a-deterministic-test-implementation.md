# ADR 0099: The HUB verifier is one interface, with a deterministic test implementation

- Status: Accepted
- Date: 2026-10-09
- Meets: [`first-goal.md`](../project/first-goal.md) requirement 4
- Changes no contract: every signature it produces is one
  [`economy-transition-v9`](../specifications/economy-transition-v9.md) already
  checks

## Context

Version nine checks two kinds of HUB proof:

- **a registration** (kind 10) carries the ecosystem verifier key's signature
  over the registration message, and the person's own HUB key signs the
  envelope;
- **every other HUB proof** is the person's HUB key: a signature in the body
  over one of five action messages (kinds 2, 3, 4, 5, 17, 18, 19, and 22), or
  the envelope signature itself for identity administration (kinds 13 to 16).

[ADR 0048](0048-hub-verification-runs-locally-with-an-ai-integrity-monitor.md)
puts the production verifier on the person's Founder Machine, sandboxed. It
derives the HUB key from a biometric capture that never leaves the sandbox.
That verifier needs a stabilization scheme still awaiting review, so it cannot
be built yet. Until now, every fixture held every person's HUB key itself and
signed by hand, so nothing stood where the verifier will stand.

Requirement 4 asks for a deterministic test verifier "as a replaceable
component", behind the interface a production verifier will implement.

## Decision

### 1. One C++ interface, `protocol::hub::VerifierV9`

`include/protocol/hub/verifier_v9.hpp` declares it. It has two operations:

- `register_person(chain_id, capture, first_signer_public_key,
  valid_until_height)` returns the **whole signed kind-10 transaction**. The
  verifier key signs the body and the derived HUB key signs the envelope, so
  no caller ever holds the HUB key.
- `approve(capture, unsigned transaction, acting escrow)` returns **the HUB
  proof that transaction needs**. For kinds 13 to 16 that is the whole signed
  transaction. For the eight body-carried kinds it is the 64-octet HUB
  signature, which the signer's envelope then covers.

Both return a `Decision`: the identity the capture belongs to, and either the
proof or a refusal.

**The verifier builds every message it signs.** It decodes the transaction and
derives the action message from its fields, with the kernel's own builders. It
never signs bytes a caller supplies. A verifier that signed an opaque digest,
as a WebAuthn assertion does, would give a compromised wallet a HUB signature
for any action it chose. The person approves a transaction, and the verifier
knows which one.

The acting escrow is an input because kinds 17 and 19 bind it, and their bodies
do not carry it. A signer resolves to its escrow only on chain. If the escrow
is not the person's, the chain refuses the proof as `UNAUTHORIZED`, and the
verifier needs no state to stay safe.

**A posture change is signed whichever way it goes.** Only a relax needs a
proof, and a tighten must carry none. Telling the two apart needs the stored
posture, which the verifier does not hold, so the wallet decides whether to
include the signature.

### 2. Four refusals

- `not_the_person`: a kind-13 to 16 transaction names an identity, or an
  authority key, that the capture does not derive. This is the stand-in for
  "this is not the enrolled person".
- `not_a_hub_decision`: kinds 1, 6, 10 (through `approve`), 20, and 21 take no
  HUB proof.
- `wrong_scheme`: a kind whose scheme does not match the one it permits.
- `malformed`: a body that does not decode for its kind.

### 3. The test verifier is a labelled stand-in

`TestVerifierV9` is deterministic, with no clock, randomness, or state. It
takes a `Capture` holding a 32-octet secret, which stands for the stable
secret a production verifier would derive from a face:

```text
hub_identity_hash = H(D("protocol-stack:hub-test-verifier:identity") || secret)
hub_key_seed      = H(D("protocol-stack:hub-test-verifier:hub-key")  || secret)
hub keypair       = Ed25519 seed keypair of hub_key_seed
verifier keypair  = Ed25519 seed keypair of a configured 32-octet seed
```

`H` and `D` are the kernel's domain-separated SHA-256, and libsodium does all
signing. One secret derives both the identity and the key, as one biometric
will. The labels name no consensus artifact.

**It is a stand-in, and says so.** It is in no node's link line, and it never
decides whether a capture is a live, unique human. The production verifier,
its stabilization scheme, and its match threshold remain founder-reserved and
owe independent review (ADR 0048).

### 4. One command, `protocol-hub-test-verifier-v9`

The command exposes the class to any harness:

```text
protocol-hub-test-verifier-v9 key      <verifier-seed>
protocol-hub-test-verifier-v9 register <verifier-seed> <chain-id> <secret> <first-signer> <valid-until>
protocol-hub-test-verifier-v9 approve  <verifier-seed> <secret> <unsigned-transaction> <acting-escrow>
```

Every argument is hex except the height. It prints `key=value` lines and exits
3 on a refusal, naming it.

## Alternatives rejected

- **A Python verifier class used by the fixtures.** It is the cheapest, but a
  production verifier in another language could not implement it. It would
  also be a third construction of the HUB messages, beside the kernel's and the
  model's.
- **A long-running socket service.** A production verifier will be one, but
  its transport depends on M5's packaging and M10's wallet. One command is the
  smallest process boundary, and the class is the interface.
- **Signing an opaque digest.** Rejected under decision 1.

## Consequences

- **Requirement 3 rebinds the registration, and requirement 5 the approvals.**
  The registry replaces the verifier key with a machine's attestation key. The
  envelope will change what an approval binds. The interface takes a capture
  and a transaction, so neither replaces it.
- **The network fixtures still sign by hand.** Moving them onto the verifier
  changes every identity they derive. It waits until requirements 3 and 5 have
  changed what the fixtures build anyway.
- **Evidence.** `hub-test-verifier-v9` executes every kind except the mints
  through the version-nine kernel, with real Ed25519, and checks every refusal.
  The mints check `NOTHING_TO_MINT` before their confirmation, so a fresh chain
  cannot reach it, and their proofs are verified against the kernel's own
  builder. `hub-test-verifier-v9-cross` runs the command on transactions the
  Python model encodes, and verifies every output with the model's own message
  constructions.
- **It confirms requirement 5's finding by execution.** `hub-test-verifier-v9`
  records that version nine accepts a HUB approval replayed under a new nonce.
  A published posture relax undoes a later tightening with a signer key alone,
  and one transfer confirmation moves value twice. Requirement 5's contract
  must refuse both, and that check is the one that will flip.

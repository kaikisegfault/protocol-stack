# HUB verification threat model

Status: first version, 2026-10-09. It meets
[`first-goal.md`](../project/first-goal.md) requirement 7 and owes the
independent review it names. It establishes nothing about whether face
verification is secure.

[ADR 0048](../decisions/0048-hub-verification-runs-locally-with-an-ai-integrity-monitor.md)
and the constitution both require this document. It covers three things:

- HUB verification as ADR 0048 places it: local, sandboxed, on a Founder
  Machine, with the local model as the integrity monitor;
- the HUB surface version nine executes today;
- the test verifier that stands in for the production one (ADR 0099).

It does not cover consensus, bridges, or AI judgment beyond the monitor.

## What is protected

- **Uniqueness.** One person holds one identity. The entry airdrop of 1.71
  units, the 1,000-seat bound, and self-referral refusal are all exactly as
  strong as this.
- **Control of an identity.** The HUB key authorizes everything a signer
  cannot: adding and revoking signers, creating and deleting escrows, relaxing a
  posture, buying and activating a seat, and confirming a transfer or a mint.
  The HUB key acts as the person.
- **Biometric material.** Captures, templates, and anything derived from them
  that could recover a face. The constitution says they never become ordinary
  chain data, and ADR 0048 says they never leave the sandbox.
- **Admission.** Who may register, and that no single party can stop someone
  registering.

## Who attacks

| Attacker | Holds | Wants |
| --- | --- | --- |
| A thief | one signer key, from a stolen device | value in that escrow |
| A hostile wallet or app | the person's attention | a HUB approval for an action the person did not intend |
| A self-verifier | their own Founder Machine | identities that are not distinct people |
| A Sybil farmer | photos, masks, synthetic media | many registrations, for airdrops and seat bounds |
| A coercer | the person, physically | an approval given under duress |
| A key holder | the verifier key, or a build-signing key | mass false registration |
| A breacher | one machine's vault | the replicated commitments and their helper data |
| An observer | the public chain | who did what, and who is who |

## The trust boundaries

```text
person --capture--> sandbox: deterministic verdict + AI integrity monitor
                       |
                       | signs with the machine's attestation key (registration)
                       | or the person's HUB key (everything after)
                       v
                    transaction --> chain: checks signatures, never the capture
```

**The chain checks signatures, and nothing about how they were made.** Version
nine verifies a registration against one genesis key and every later proof
against the person's recorded HUB key. Everything about whether a live,
distinct person stood behind a signature happens inside the sandbox, and the
chain sees none of it.

## Threats

Each entry states what stops it today, what the next contract version must add,
and what is owed to review. "Version nine" means the contract the chain runs
now.

### T1. An approval used twice: executed

**Version nine accepts it.** `hub-test-verifier-v9` runs it: Alice relaxes her
posture with a HUB approval and tightens it again with her signer. The
published relax is then accepted again under a new nonce. One transfer
confirmation also moves value twice. No HUB message binds a nonce, and the
kernel checks `valid_until_height` only from below, so an approval lasts as
long as its author let it. The fixtures use height 10,000,000,000.

**The posture case defeats a founder rule.** ADR 0043's asymmetry exists so
that a stolen signer key cannot weaken the protection it is stealing against.
Replaying a published relax does exactly that.

**Requirement 5 must close it.** Every approval must be single-use, by binding
the escrow's nonce or a decision identifier the chain records. Its validity
must also be bounded by the protocol, not by the wallet. Both change message
bytes, so this needs a new contract version.

### T2. A verifier tricked into signing something else

A verifier that signed whatever digest a wallet handed it would give a hostile
wallet a HUB approval for any action. **The test verifier builds every message
it signs from the transaction it is shown** (ADR 0099). The production verifier
must do the same, and must also show the person what they are approving. That
second half is a requirement on the wallet and the capture interface, and
nothing exists for it yet.

### T3. A key derived from a face is only as secret as the face

**A face is not a secret.** Photos are public. If a HUB key were derived
deterministically from a face alone, anyone holding a good enough image and the
public derivation could compute the key offline. They would need no liveness
check, because they would never visit a sandbox. The monitor and liveness
checks protect only a verification that actually runs.

**So the HUB key cannot be a function of the biometric alone.** It must also
depend on a secret that only an attested sandbox holds. ADR 0048's
"multisignature vaults" point this way, but nothing specifies it. That raises
two design questions:

- where that secret lives for a person who owns no Founder Machine, which is
  requirement 3's first question in another form;
- how recovery on a different machine reaches it. A threshold share across
  several machines is the standard answer.

The test verifier's stand-in has exactly this weakness on purpose: its secret
stands for the stable output of a face, and whoever holds it holds the key.

### T4. A founder verifying themselves

ADR 0048 runs verification on the founder's own machine. A founder who defeats
that machine's attestation defeats both the verifier and its monitor, and can
then attest identities that are not distinct people. **ADR 0048 states this
risk, and nothing solves it.** The monitor raises the cost from trivial to a
compromised attested build. Hardware the ecosystem produces is the strongest
mitigation, and it does not exist yet.

### T5. A Sybil at population scale

**Uniqueness is unenforced today.** The chain stores a 32-octet commitment per
identity and catches no duplicate, because two captures of one face never
produce the same bytes. ADR 0048's answer is a stabilization step, a fuzzy
extractor or secure sketch, so that one face yields one commitment and every
machine can compare locally. **Nothing is built on it until it passes
independent cryptographic review.**

Checking one capture against a whole population is 1:1 matching applied N
times, so false accepts grow with N. The false-acceptance target must be chosen
against the target population, a million identities for the airdrop, not
against a demonstration.

Helper data is its own exposure. A secure sketch's public helper data can leak
information about the biometric. Reusing one face across several enrollments
has known attacks, which is why the literature's "reusable" extractors exist.
Replicating helper data to every machine multiplies that exposure.

### T6. A presentation attack

Photos, replayed video, masks, and synthetic media injected below the camera.
The deterministic verdict cannot tell a live face from a replay. **Liveness is
the monitor's to judge**, and ADR 0048 gives it authority to reject a run and
force it to restart. No liveness method is chosen, and the choice owes review.

### T7. A coerced approval

A biometric approval proves who was present, not that they consented. The
constitution requires coercion limits, and nothing specifies them. Candidate
controls include a delay before a large relaxation takes effect, and a duress
gesture. Each changes what a person experiences, so each is the owner's to
decide.

### T8. A compromised registration key

**Version nine has one verifier key, written at genesis.** Whoever holds it can
register people who do not exist. Each one draws the 1.71-unit airdrop while
fewer than a million are enrolled, and gains a seat bound of its own. It cannot
touch anyone already registered (ADR 0036). No transition rotates or revokes
it.

**Requirement 3's registry spreads this across machines**, and ADR 0048 is
explicit about what remains: whoever signs the attested build is the root of
trust, and during initialization that is the company. A compromised
build-signing key means attested builds that lie. Rotating and renouncing that
key is founder-reserved.

The registry should also bound what one compromised machine can do, for example
with a registration rate per machine. That is a candidate for the contract
version to evaluate. It changes how fast a newcomer can join, so its value is
asked, not chosen.

### T9. A HUB key that can no longer be produced

**No transition rotates a HUB public key** (ADRs 0036, 0039, and 0044). If the
key derives from a face and a vaulted secret, "losing" it means the face drifted
past the stabilization tolerance, or the vaulted secret was lost. Ageing and
injury make the first likely over a lifetime. A strict posture plus an
unreachable key is an escrow locked for good, with a nonzero balance.

Who may authorize re-binding a person to a new key is founder-reserved. It is
the same authority question as T8, asked about one person instead of a machine.

### T10. The monitor attacked

The monitor is a model, and a model can be manipulated by its inputs. Its
authority is only to dispute, reject, and restart, so a manipulated monitor
fails closed. It can deny a legitimate person and cannot admit a false one,
unless it is the only check standing. The cost of failing closed is denied
admission and denied recovery. How often a person may retry, and what happens
after repeated rejection, belongs to the AI framework, which is
founder-reserved.

### T11. Linking a person's activity

**Every escrow a person holds is publicly linkable to every other.** An escrow
identifier is derived from the identity hash and an index (ADR 0044), and the
derivation is public, so anyone can enumerate a person's escrows from one of
them. The design chose it so a wallet can compute its own identifiers offline.
Its cost is that holding several escrows gives no on-chain privacy between
them. The constitution's unlinkability requirement is stated for biometric
linkage data, and this is linkage of activity. It is recorded so that nobody
mistakes several escrows for several personas.

The uniqueness commitment, once stable, is the same value for one face on any
system that uses the same extractor. It must be keyed per ecosystem, or it
becomes a cross-system identifier for a face.

## Already handled in version nine

- **Cross-chain replay**: every HUB message binds the chain identifier.
- **Cross-action replay**: every message binds its action's fields. A mint binds
  its kind, seat, and destination, a transfer its recipient and amount, and a
  relax the exact posture. `hub-test-verifier-v9` executes the kind and amount
  bindings.
- **Cross-person replay**: every message binds the identity.
- **Registration replay**: an identity already registered, or a first signer
  already assigned, is `REPLAY`.
- **Unsigned transactions reaching execution**: scheme 2 puts the HUB key in the
  header, so admission verifies the signature without reading state (ADR 0044).
- **A verifier holding state it should not**: the test verifier holds no chain
  state, and the chain refuses an approval for an escrow the person does not
  own.

## What the next contract version must do

The version that carries requirements 3 and 5 must:

1. make every HUB approval single-use, bound to a nonce or a recorded decision
   identifier, with a protocol-bounded validity window (T1);
2. replace the genesis verifier key with the per-machine attestation-key
   registry, whose members are active, attested machines (T8);
3. state how a registry key is revoked when its machine stops being active or
   attested (T8);
4. evaluate a per-machine registration bound, and ask its value (T8).

It must not settle T3's vaulted secret, T5's stabilization, or T9's rotation
authority by default. Each one is either founder-reserved or owes review first.

## Owed to independent review

These add to the list in
[`founder-economy-devnet-audit-v1.md`](../project/founder-economy-devnet-audit-v1.md):

1. the stabilization scheme, its helper-data leakage, and its reusability (T5);
2. the false-acceptance target against a million identities (T5);
3. the liveness method (T6);
4. key derivation from a biometric and a vaulted secret, and its threshold
   recovery (T3);
5. attestation on software-only machines, against a founder with physical
   access (T4);
6. the single-use approval construction, once specified (T1).

## Founder-reserved, surfaced here

- where a person without a Founder Machine is verified, and where their
  vaulted secret lives (T3, requirement 3);
- how the first registrations happen before any machine is active
  (requirement 3);
- coercion controls (T7);
- who may rotate the build-signing key, a registry key, or a person's HUB key
  (T8, T9);
- what happens after a person is repeatedly rejected (T10);
- the value of any per-machine registration bound (T8).

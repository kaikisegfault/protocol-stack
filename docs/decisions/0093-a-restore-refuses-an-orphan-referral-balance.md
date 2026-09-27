# ADR 0093: A restore refuses a referral balance no seat's referrer owns

- Status: Accepted
- Date: 2026-09-27
- Closes: the gap [ADR 0092](0092-the-version-eight-deletion.md) recorded
- Extends: [ADR 0080](0080-the-version-nine-snapshot.md)'s restore rules

## Context

ADR 0066's third restore gate promises that a restore hands back a state some
sequence of blocks could have produced, or nothing. Every restart of a
version-nine node depends on that promise, because the owning store holds the
head as one snapshot payload and reopens it through the same decoder
([ADR 0081](0081-the-version-nine-owning-store.md)).

While porting version eight's snapshot refusals, M3.20k found a state the gate
admits and no block writes. **A referral balance keyed to an identity no seat
names as its referrer restores, provided it owes nothing.** Gate 3's referral
check sums what balances owe, and an orphan that owes nothing adds zero. An
orphan that owes anything is refused, so no unit can be minted from one. But a
node restored from such a payload would hold a root no network produced.

**Two facts make the orphan unreachable, and both are read from the transitions
rather than assumed.** A referral balance is written in one place,
`apply_assignment` in `src/v9/economy_assignment.cpp`. It accrues to
`seat.referrer_hub_identity` for an in-scope seat with a referrer and to nobody
else. And the seat table only grows: no transition erases a seat or rewrites
its referrer, and a purchase refuses to name its own buyer. The same write
shows a second unreachable state. **Every accrual is a whole referral leg**, and
`accrued` never falls, so a balance whose `accrued` is zero is a second
encoding of absence.

## Decision

**Two rules join the version-nine snapshot decoder.**

1. `apply_referral_balance` refuses a value whose `accrued` is zero, beside
   its existing refusal of `minted` above `accrued`. It is the monthly claim's
   zero rule, stated for the balance that claim was modelled on.
2. `complete` refuses a referral balance whose identity is not the referrer of
   any seat in the payload. It runs once every entry is in, beside the rule
   that refuses an uptime entry, a monthly figure, or a monthly claim naming a
   seat the chain never sold. So no value decoder depends on kind 1 sorting
   before kind 4.

**Both are storage rules, and that is the reason they live here.** The
alternative was a clause in `conservation_failures`. That function is the
kernel's invariant set, and execution reads it too, so a stricter clause there
would be a consensus-visible change needing its own version. In the snapshot
decoder the rules can only refuse a payload no block wrote. No block's
acceptance and no state root moves, and nothing outside storage changes.

## Evidence

`snapshot_v9_inherited_refusals.cpp` gives the settled chain's last seat a
referrer. The referrer is a registered identity other than the seat's owner,
because a purchase refuses to refer oneself. The payload is resealed and must
restore before any case uses it. Then:

- a fully minted balance that referrer owns restores;
- the same balance on the payload where no seat names it is refused as
  `invalid_state`;
- a balance that accrued nothing is refused as `invalid_state`;
- the inherited rule, minted above accrued, is refused, with its control now on
  a balance the referrer owns, so nothing but the value is wrong. The control
  still stops at gate 3.

**The first pair is the one that matters.** It differs in the seat's referrer
flag and nothing else, and the balance owes nothing, which is exactly the case
gate 3 cannot see. Removing each rule fails its case by name, and every suite
that restores a recorded version-nine chain still passes: the snapshot, the
owning store, recovery, the application, the transport, and the headless
process.

## Consequences

**Restore is stricter by exactly two unreachable states.** No recorded chain,
devnet run, or vector file carries either, because no transition can write one.

**The referral balance is the first inherited kind whose cross-entry rule is
version nine's own.** Version eight's decoder had the same gap, and it is not
repaired there. Version eight is deleted.

**What gate 3 still cannot see is history.** A seat whose referrer flag is set
long after its referral legs went to the unreferred pool is shaped lawfully and
restores. A snapshot holds a state, not the blocks that produced it, so a rule
over history needs a record of history. That record belongs to the archive,
not to this decoder.

# ADR 0094: A new referral balance starts at the window before its first accrual

- Status: Accepted
- Date: 2026-09-27
- Repairs: every executed model from `economy-transition-v6` onward, and the
  version-nine C++ kernel
- Rule repaired to: [`economy-transition-v3`](../specifications/economy-transition-v3.md)
  §The referral balance, carried unchanged by versions six through nine

## Context

The accumulation cap applies to a referrer as it does to a seat. A referrer
accrues in window `w` only when

```text
w <= collected_through_window + MINT_ACCUMULATION_CAP
```

and a kind-5 mint sets `collected_through_window` to the last assigned window.
Version three states where the mark starts:

> The entry is created lazily, at a referrer's first accrual, with
> `collected_through_window` set to the window before that accrual, so a
> referrer is never capped before anything has been credited to them.

Version six says its cycle assignment is "unchanged from version three in every
respect". Version nine incorporates by reference "every rule of versions one
through seven — the settlement's eight steps and their order … the accumulation
cap". So the rule is normative for the chain that runs today.

**No executed implementation follows it.** Version six's Python ledger created
the balance with a default value whose mark is zero, version seven copied that
line, and versions eight and nine inherit version seven's. The version-nine C++
kernel does the same with a default-constructed map entry.

Planning the fourth scenario suite found it, before any code was written, while
deriving the population's referral schedule. The consequence is exact and
large. **A zero mark agrees with the rule only while the first accrual lands in
windows 1 to 30.** After that, the referrer is over the cap from their second
accrual onward, so every later leg of every seat they referred goes to the
unreferred pool until they mint. On a chain a day per window, that is every
referral whose seat activates after the first month.

A scratch run on the version-nine model confirmed it before anything changed. A
seat referred and activated in window 100 credited its referrer one leg in
window 101, and then sent windows 102 onward to the unreferred pool.

**No recorded vector reaches it.** Every recorded referral is minted in the same
block that makes its first accrual. The mint moves the mark to the last assigned
window before a root commits to the zero. Every accepted vector file from
version six to version nine was re-run against the corrected models. All 2,977
vectors pass unchanged:

| File | Vectors |
| --- | ---: |
| `economy-transition-v6.txt` | 462 |
| `economy-transition-v6-execution.txt` | 512 |
| `economy-transition-v7.txt` | 395 |
| `economy-transition-v7-execution.txt` | 590 |
| `economy-transition-v8.txt` | 183 |
| `economy-transition-v8-execution.txt` | 434 |
| `economy-transition-v9.txt` | 239 |
| `economy-transition-v9-execution.txt` | 162 |

## Decision

**Repair the implementations to the accepted rule, inside version nine.** A new
referral balance is created with `collected_through_window = w - 1`, where `w`
is the cycle window whose accrual creates it. The change is made in three
places:

- `first_referral_balance` in `simulation/economy_transition_v6/ledger.py`,
  called by the version-six ledger and by version seven's, which versions eight
  and nine inherit;
- `apply_assignment` in `src/v9/economy_assignment.cpp`;
- a zero window, which no accrual can have because no seat is in span before
  window 1, is refused in both, not wrapped.

**This is a conformance repair and not a new version.** Version nine's
versioning section requires a new transition version for "a changed field, code,
order, or semantic rule". No field, code, or order changes. The semantic rule is
the one the specifications already state, and the implementations did not
follow it. The alternative was a version ten whose only change is to execute a
sentence version nine already contains. That would carry the defect forward as
version nine's accepted behaviour. It would also cost a full stack migration,
because each earlier version change moved the store, the snapshot, the
application, the transport, and the adapter. No persistent network exists to
migrate. The devnet runs are CI fixtures, and none reaches window 30.

**The deleted C++ versions are not repaired, because they no longer exist.**
Version eight's C++ kernel went in M3.20k and version seven's before it. Their
Python models are repaired, because version nine's model is built on them. Their
recorded vectors are unchanged.

## Evidence

- `tests/simulation/economy_transition_v9_referral_mark_test.py` registers a
  referrer and a buyer with signed transactions and sells a referred seat. It
  activates the seat in window 100 and opens every window after through the
  version-nine prologue. The referrer's balance starts at mark 100. Windows 101
  to 130 all accrue to the referrer. Window 131 is forfeited to the unreferred
  pool, so the cap still binds, measured from the repaired mark. A mint after
  the first accrual advances the mark exactly as before. Restoring the zero
  mark fails four of its nine tests by name.
- `tests/kernel/economy_v9_referral_mark.cpp`, run by
  `economy-transition-v9-execution-cpp`, drives the kernel's own
  `derive_schedule`, `derive_assignment`, and `apply_assignment` over the same
  thirty-one windows. It checks the same four facts. Built against the
  unrepaired kernel it fails on the first, "the mark starts at the window before
  the first accrual".
- Every suite that replays or restores a recorded version-nine chain passes
  locally against the repaired kernel: the snapshot, the owning store, the
  application, the transport, and both headless processes.

## Consequences

**A referrer now has thirty windows from their first accrual to collect, as
version three promised.** Nothing else about the cap changes. A referrer who
does not collect still forfeits to the unreferred pool, and the forfeited value
still stays inside the referral channel.

**The unreferred pool receives less on any chain where a late referrer does not
mint at once.** That was never the pool's value to receive. The monthly payout
ranks machines on uptime and pays whatever the pool holds, so no payout rule
changes.

**This is the second defect in this lineage that no recorded vector could see**,
after ADR 0093's orphan balance. Both were found by constructing a state the
recorded chains never reach. That is the argument for the fourth scenario suite,
which runs every seat's whole life and not a handful of chosen heights.

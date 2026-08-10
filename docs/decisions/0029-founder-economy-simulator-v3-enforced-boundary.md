# ADR 0029: Enforcing the cycle boundary and record completeness in the economy model

- Status: Accepted
- Date: 2026-08-10

## Context

[ADR 0027](0027-founder-cycle-boundary.md) accepted `cycle-boundary-v1`, which
defines the window a cycle is cut from and the predicate that decides whether a
supplied window is the window for a supplied cycle index.
[ADR 0028](0028-uptime-measurement-pipeline.md) accepted
`uptime-measurement-v1`, which produces a complete `cycle_uptime_record` for a
finalised window.

Neither is applied. `founder-economy-simulator-v2` still records two gaps under
its own "What this model does not establish": the mapping from a seat's
`cycle_index` to a `cycle_window` "is not defined or checked", and "a record that
omits seats is not detected". Both specifications say explicitly that closing
them changes a transition, which under the rule ADR 0024 and ADR 0026
established requires a new economy contract version rather than an edit, and both
name that version as M3.6.

Requirements 8 and 9 of [`first-goal.md`](../project/first-goal.md) are
therefore satisfied in specified form and not in enforced form. This ADR records
the decisions that close that distance.

## Decision

### One economy version carries both changes

`uptime-measurement-v1` established that the record's denomination is stable:
`uptime_seconds` remains the unit, and a pipeline emitting whole hours is a
strict subset of the `0..86,400` range version two already validates. The
cycle-boundary check and the completeness check therefore do not need the record
to change shape, and neither depends on the other having landed first.

The alternative — one version applying the boundary check and a second applying
completeness — was rejected because it would spend two contract versions, two
sets of labels, two vector files, and two verifiers where one does, and because
each version would be accepted while still recording the other's gap.

### The manifest is not re-versioned

No channel, cap, base leg, denomination, subtotal, beneficiary kind, seat
capacity, per-person bound, or issuance-cycle count moves. `founder-economy-
manifest-v2` is the same 2,267-byte artifact with the same digest, so version
three loads it rather than restating it.

Re-versioning the manifest alongside the simulator was considered for symmetry
and rejected. A manifest version names an exact byte string that evidence was
verified against; minting a second name for identical bytes would make the
digest stop identifying the contract, which is the property ADR 0024 introduced
version labels to preserve.

### A sibling package, not a `Binding`

ADR 0026 chose a `Binding` record over a second package for `escrow-payout-v2`,
because the two versions differed in exactly six strings and every transition was
identical. It also recorded the condition under which that choice inverts: "that
would become the wrong one if a version three revised a payout rule; at that
point option 1 becomes correct for the diverging transition."

That condition is met here. `activate_seat` takes a new input, the seat record
changes shape, `evaluate_base_permission` gains six rejection conditions, the
canonical state gains two members, and the state invariants gain three clauses.
A `Binding` would have to select behavior rather than strings, which is a branch
inside every affected transition and exactly the drift risk the escrow decision
avoided by having none.

`simulation/founder_economy_v3/` is therefore a sibling of
`simulation/founder_economy_v2/`, as that package is a sibling of
`simulation/founder_economy/`.

### The manifest layer is bound, not copied

Version three does not duplicate `manifest.py`, `manifest_fields.py`, or
`derivations.py`, and does not restate the channel table, caps, legs,
denomination, or cycle time constants. It reads them from the accepted v2
manifest contract.

Copying them was rejected on the same ground ADR 0026 rejected a duplicate escrow
package: three loaders for one byte-identical accepted artifact would be three
implementations of one contract with nothing keeping them equal, and the failure
would be silent. The rule applied is that a version owns what its behavior
changes and binds what it does not.

The consequence accepted is a package dependency from v3 to v2. It is one
direction only — v2 imports nothing from v3 — and a future version that revises
the manifest would need its own manifest layer, which is visible at the import
rather than hidden in a copied table.

### The grid is bound, and no schedule state is bound with it

The window functions are imported from `simulation/cycle_boundary/`, and the
model asserts that its view of the shared founder-directed figures equals that
contract's rather than holding a second opinion.

A digest bind of a recorded cycle-boundary **state**, in the style
`escrow-payout-v1` established and `uptime-measurement-v1` reused, was considered
and rejected. Those models bind a foreign state because they are readers of
something another model wrote. Here the economy model is the **writer**: it is
the transition that records an activation, and `cycle-boundary-v1` says outright
that it "takes an activation height as given". Binding a second activation table
would create a schedule that could disagree with the seat table this model holds,
and in a consensus implementation the two are one chain state, so the
disagreement would be unrepresentable there and only reachable in the model.

Agreement is instead required by construction and proved externally: the verifier
runs the cycle-boundary model over the same activation heights and requires
identical answers for every checked window, including the three rejection codes.

### Monotonicity moves to the writer

`cycle-boundary-v1` rejects an activation height below the last recorded one,
and states why: a real activation executes inside the block that includes it, so
a replayed or reordered activation must not install a schedule in the past. That
model cannot enforce it against the economy model's seat table, because it does
not hold it.

Version three therefore enforces `HEIGHT_NOT_MONOTONIC` in `activate_seat`.
Leaving it out was rejected because the containment would then be stated in one
accepted artifact and applied in none. Equal heights stay accepted, because one
block may activate several seats.

### The in-scope set has no upper bound

A seat is in scope for window `w` when its `first_cycle_window` is at most `w`.
`uptime-measurement-v1` sets no upper bound, and version three does not add one.

Bounding the set at `last_cycle_window` was considered — a seat past its 731
windows no longer issues, so it is tempting to stop measuring it — and rejected.
The Founder Constitution ends a seat's issuance period while keeping the seat
permanent and its node running, and the reallocation rule asks for the highest
uptime in the window rather than the highest among seats still issuing. Adding
the bound would narrow a founder-directed population by autonomous choice, and it
would make the producing and consuming ends derive different sets from the same
schedule, which is the one property that makes them agree.

### Completeness is two codes, not one

`SEAT_NOT_IN_SCOPE` reports a listed seat that has no evidence for the window;
`INCOMPLETE_UPTIME_RECORD` reports an in-scope seat the record omits.

One code naming the property was considered. It was rejected because the two
defects have opposite economic effects: an omission shrinks the population a
reallocation ranks over and can send a failed cycle's Founder portion to a seat
that was not the best, while an addition admits a seat with no evidence and could
make it the winner. `SEAT_NOT_IN_SCOPE` reuses the name
`uptime-measurement-v1` already gives the same concept, so the producing and
consuming ends describe one condition with one word.

### The intrinsic checks precede the binding check

The boundary and completeness checks are properties of the record, the seat, and
the schedule alone. `INCONSISTENT_UPTIME_RECORD` is a property of the run's
history.

Placing the binding check first was considered, since it is the cheapest. It was
rejected because it would make the same defect produce two different codes
depending on unrelated history: a misfiled window would report as inconsistent
when that window happened to have been bound already and as
`WINDOW_NOT_FOR_CYCLE` otherwise. Both orders are deterministic; only this one
makes a code mean one thing. A rejected event binds nothing, so a defective
record cannot occupy a window and make a later correct record inconsistent with
it.

### Heights are strings and windows are numbers

An `activation_height` is a canonical unsigned decimal string wherever it
appears, because a `u64` height exceeds `MAX_JSON_INTEGER` and could not be
canonicalized as a number. That is `cycle-boundary-v1`'s rule and version two's
rule for monetary values.

A window stays a JSON number, which `cycle-boundary-v1` does not do. The reason
is derived rather than stylistic: `MAX_WINDOW` is `MAX_HEIGHT / 28,800`, which is
640,511,947,003,803 and is more than a factor of fourteen below
`MAX_JSON_INTEGER`, so every window reachable from a representable height is an
exact JSON number. Rendering windows as strings for uniformity would have changed
`cycle_window` inside the `cycle_uptime_record`, and holding that shape fixed is
what lets `uptime-measurement-v1` feed this version with no new version of its
own. The inequality is recorded as a derived vector rather than assumed.

### The seat's span endpoints are recorded in the state

`first_cycle_window` and `last_cycle_window` are derived from the activation
height and are stored in the canonical state anyway.

Omitting them was considered, since a digest should not carry redundant derived
data. It was rejected because storing them puts the grid inside the state digest:
a change to `CYCLE_BLOCKS` then changes every state digest, rather than silently
renumbering every window behind a digest that did not move. It also lets a reader
check a pending permission's `cycle_window` against its seat's span without
replaying the run.

## Consequences

- `simulation/founder_economy_v3/` implements the accepted version-three
  contract. `simulation/founder_economy/` and `simulation/founder_economy_v2/`
  are untouched, and their vector files, digests, and tests are byte-for-byte
  unchanged and continue to pass.
- `test-vectors/founder-economy-simulator-v3.txt` is new and normative.
  `tools/founder-economy-v3-vectors/` verifies it, and its `expected.py` imports
  nothing from `simulation/`.
- Requirements 8 and 9 of `first-goal.md` move from specified to enforced.
  Requirement 4's predicate is applied for the first time.
- Two of the seven items version two records under "What this model does not
  establish" are closed. The other five are unchanged and are restated in the
  version-three specification rather than dropped.
- `escrow-payout-v2` and `economy-scenario-suite-v2` still bind version two.
  Rebinding them is the next slice and is `escrow-payout-v3` and
  `economy-scenario-suite-v3` rather than an edit, on the same grounds.
- No C++, consensus, devnet, bridge, wallet, AI, biometric, or resource behavior
  changes. The model activates nothing and issues no native unit.

## Compatibility and independent review

Versions one, two, and three coexist. Every version-three domain label ends in
`-v3`, so no digest computed under one version can be replayed as another, and
the inherited manifest label is the only shared one because the manifest is
genuinely the same artifact.

This slice proves that a supplied window is the window the accepted grid assigns
to a seat's cycle, and that a record covers exactly the population the accepted
schedule says was running. It proves nothing new about whether that population
was operational.

The claims ADR 0027 and ADR 0028 refer to independent review are unchanged and
are not narrowed by this slice: that the grid is safe against an adversary able
to influence block production rate, that an answered challenge reflects a real
machine, that the sampling margin is adequate against a founder with physical
machine access, and that beacon bias is tolerable. Enforcing a schedule against a
measurement does not make the measurement sound. No independent security review
has occurred.

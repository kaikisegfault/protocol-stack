# ADR 0103: The registry count excludes an unmarked machine

- Status: Accepted
- Date: 2026-10-10
- Repairs: [`economy-transition-v10`](../specifications/economy-transition-v10.md)
  §The registry step, step 2, before anything implements it
- Restores: the founder answer in
  [ADR 0101](0101-founder-answers-on-the-launch-cutoff-an-active-machine-and-the-registration-limit.md)
- Found by: M4.3c, the version-ten execution model's first population

## Context

The registry step runs at every assignment. Step 1 marks each machine whose seat
met the due window, and step 2 counted "the machine-key entries whose
`last_met_window` equals the due window". The machine-key entry encodes "never
met" as a mark of 0, and the specification argues that 0 is unambiguous,
because no seat is in scope for window 0.

**That argument holds for the activity test and fails for the count.** At the
first assignment the chain performs, at height 57,600, the due window is 0. No
seat is in scope, so step 1 marks nothing. But every key registered before then
holds a mark of 0, and 0 equals the due window, so step 2 counted every one of
them. A chain with 100 machine keys registered in windows 0 and 1 retired the
launch key at height 57,600, before any machine had met any cycle.

The founder's answer is that the launch key retires once 100 machines are
active, and that an active machine is one whose seat met its most recently
assigned cycle. A machine that has never met a cycle is not active, so the
literal step 2 contradicted the answer it encodes.

**The execution model found it.** Its first population registers 101 keys in
window 0, and the window-0 assignment retired the launch key. Every later
registration under the launch key was then `LAUNCH_KEY_RETIRED`, including the
one the vectors expected to succeed at a count of 99.

## Decision

**Step 2 counts the entries whose mark is nonzero and equals the due window.**
The text of the specification now says so, and the model implements it.

This is a repair of an unimplemented specification rather than a new version.
No kernel, store, application, or network executes version ten, no vector
recorded a retirement, and the change restores the rule the founder answer
states. Version ten's contract vectors do not reach the step and are unchanged.

### Alternatives considered

- **Skip the step at the window-0 assignment.** It removes the case without
  stating why, and a later version that moved the assignment lag would have to
  rediscover it.
- **Encode "never met" differently**, as the window plus one or with a separate
  flag. It changes an entry width the contract vectors already fix, to remove a
  case one comparison removes.
- **Count the machines step 1 marked.** It is the same number for every due
  window, but the specification computes the count from the entries on purpose,
  so that what is counted is what the state holds.

## Consequences

- The kernel must count `last_met_window != 0 && last_met_window == due`. A
  kernel that ported the old text would retire the launch key at height 57,600
  on any chain with 100 early keys, and diverge from the model at that root.
- The execution vectors record the window-0 assignment with 101 keys registered,
  a count of zero, and no retirement, next to the count of 100 that does retire.
- Nothing else moves. Activity already required a nonzero mark.

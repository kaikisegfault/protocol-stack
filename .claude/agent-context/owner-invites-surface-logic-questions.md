# Owner invites surface logic questions

On 2026-08-13 the protocol-stack owner extended their standing invitation: at
any moment I doubt that a surface-level rule, operation order, or end-to-end
user-to-system flow is right, I should ask rather than invent a placeholder and
proceed. This is broader than the founder-reserved set the founder-decision gate
covers.

**Why:** their input produces better designs, not just permitted ones. In M3.8a
their rule that "a mint takes everything, no quantity choice" removed 73,100,000
would-be state entries, because a mint that can take a chosen amount must record
which cycles it took. Their rule that "the escrows are paid at the winner's
mint" removed a failed seat's ability to withhold other parties' value forever.
Neither was reachable by inference from the accepted documents. They said
explicitly that they can reason from the whole-system perspective to the most
efficient solution that satisfies every need at once.

**How to apply:** ask early, before building. A wrong guess about operation order
is cheap in a specification and expensive once vectors, models, and an
implementation depend on it — M3.8a's first specification had to be rewritten
before merge because three guessed transitions were wrong. Keep using the
batched selectable-option call at the end of a response. Use plain language, not
internal model vocabulary: they pushed back on "evaluate / exercise / accrue"
and asked for simpler words. This does not relax any evidence gate or license
pausing for ordinary technical approval — mechanism, encoding, and naming stay
autonomous. Recorded in `CLAUDE.md` under "Ask about surface logic whenever
there is doubt".

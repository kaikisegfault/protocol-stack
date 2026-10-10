"""The version-ten Founder Economy model: `economy-transition-v10`.

Version nine with a registry of attested machine keys in place of the single
verifier key, and HUB approvals that can be used once (ADRs 0102 and 0103).

**The contract half** holds the constants, genesis, the three new state entries,
the two changed bodies, and the three new signed constructions: `contract.py`,
`genesis.py`, `state.py`, `envelope.py`, and `messages.py`.

**The execution half** runs them. `ledger.py` holds the registry beside version
nine's state; `execution.py` admits a transaction and applies the lifetime rule
straight after `EXPIRED`; `transitions.py` executes kinds 10 and 23 and hands
every other kind to version nine's own dispatch through `approval.py`, which
makes a body approval verify over the whole transaction; `block.py` adds the
registry step to the prologue; `receipt.py` moves kind 23 into the kinds that
issue nothing. `trace.py` records a chain of blocks, and `population.py` drives
101 machines through the evidence harness, both over `fixture.py`'s builders.

**Version nine is imported rather than copied.** A carried constant is version
nine's own object, and a carried function is version nine's own code, so a
width or rule that moved would have to move in an accepted module first.
"""

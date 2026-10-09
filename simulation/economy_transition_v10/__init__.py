"""The version-ten Founder Economy model: `economy-transition-v10`.

Version nine with a registry of attested machine keys in place of the single
verifier key, and HUB approvals that can be used once (ADR 0102). This package
holds the contract half: the constants, genesis, the three new state entries,
the two changed bodies, and the three new signed constructions. The execution
half, kinds 10 and 23 against a ledger and the registry step, follows it, as
version nine's did.

**Version nine is imported rather than copied.** A carried constant is version
nine's own object, and a carried function is version nine's own code, so a
width or rule that moved would have to move in an accepted module first.
"""

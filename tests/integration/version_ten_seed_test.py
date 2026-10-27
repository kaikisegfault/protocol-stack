#!/usr/bin/env python3

"""A model ledger, encoded in Python, seeds a version-ten C++ store.

`protocol-application-v10 --seed` accepts a payload only through
`decode_snapshot_v10`'s gates, the retirement rule among them, and only if it
re-encodes to exactly its own octets (ADRs 0096 and 0108). So each seed below
checks two things at once. The model's state is one a chain could hold. And
`version_ten_snapshot.encode` writes the bytes the C++ encoder would.

**Four ledgers are seeded, chosen for what they carry.**

- The restart run is five contiguous blocks: identities, escrows, two seats,
  and both machines registered through kind 23.
- The recorded chain has run past its activation height. It carries uptime and
  assignment records, typed custody, the recovery pool, the monthly figures and
  a claim, a referral balance, and a founder's registrations through a machine.
- The same chain, run on to the first height with a challenge outstanding.
- The cutoff population is 101 machines at window 33. It carries the launch
  key's retirement, which only 100 active machines write.

Between them they carry every entry kind version ten writes. Kind 5, the direct
decision, is the exception, and no block can write it while kind 6 refuses
every sender. The test requires that coverage instead of asserting it. Each seed
must print the model's chain identity, height, stamp, and root, and
`--inspect-seed` must print exactly the same four lines before the store exists
and after it does (ADR 0097).

**Five seeds are refused, and a refusal must leave no file.** Inspection must
refuse the four that are about the payload rather than the path:

- a payload with one octet changed;
- a seed onto an existing store;
- the same state under another chain's genesis;
- the same state under a genesis whose build authority key differs, which is
  version ten's own;
- a height-zero payload, which is a genesis rather than a seed.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
from dataclasses import replace

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
for _entry in (REPOSITORY, pathlib.Path(__file__).resolve().parent):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

from simulation.economy_transition_v10 import contract as c  # noqa: E402
from simulation.economy_transition_v10 import fixture  # noqa: E402
from simulation.economy_transition_v10 import genesis as g  # noqa: E402
from simulation.economy_transition_v10 import population  # noqa: E402
from simulation.economy_transition_v10 import trace  # noqa: E402
from simulation.economy_transition_v10.block import run_quiet_heights  # noqa: E402
from simulation.economy_transition_v10.ledger import Ledger  # noqa: E402
from version_ten_snapshot import encode  # noqa: E402

# No block writes a direct decision while kind 6 refuses every sender.
UNREACHABLE_ENTRY_KINDS = {c.DIRECT_DECISION_ENTRY}
# How far past the chain's end a challenge must appear. One appears 383 heights
# after it; the bound keeps a regression from running forever.
CHALLENGE_SEARCH_HEIGHTS = 30_000


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def seed(application: pathlib.Path, database: pathlib.Path,
         genesis: pathlib.Path, snapshot: pathlib.Path):
    return subprocess.run(
        [str(application), "--seed", str(database), str(genesis), str(snapshot)],
        capture_output=True, text=True, timeout=120, check=False,
    )


def inspect(application: pathlib.Path, genesis: pathlib.Path,
            snapshot: pathlib.Path):
    return subprocess.run(
        [str(application), "--inspect-seed", str(genesis), str(snapshot)],
        capture_output=True, text=True, timeout=120, check=False,
    )


def identity_of(output: str) -> dict[str, str]:
    values = dict(line.split("=", 1) for line in output.strip().splitlines())
    require(set(values) == {"chain_id", "height", "timestamp", "app_hash"},
            f"the seed printed {sorted(values)}")
    return values


def check_seed(application: pathlib.Path, directory: pathlib.Path,
               name: str, ledger: Ledger, genesis_bytes: bytes) -> bytes:
    genesis = directory / f"{name}.genesis"
    genesis.write_bytes(genesis_bytes)
    payload = encode(ledger)
    snapshot = directory / f"{name}.snapshot"
    snapshot.write_bytes(payload)
    database = directory / f"{name}.sqlite"
    before = inspect(application, genesis, snapshot)
    require(before.returncode == 0,
            f"{name}: the inspection was refused: {before.stderr.strip()}")
    result = seed(application, database, genesis, snapshot)
    require(result.returncode == 0,
            f"{name}: the seed was refused: {result.stderr.strip()}")
    after = inspect(application, genesis, snapshot)
    require(before.stdout == result.stdout == after.stdout,
            f"{name}: inspection and the seed report different heads")
    printed = identity_of(result.stdout)
    expected = {
        "chain_id": ledger.chain_id.hex().upper(),
        "height": str(ledger.height),
        "timestamp": str(ledger.timestamp),
        "app_hash": ledger.state_root().upper(),
    }
    require(printed == expected,
            f"{name}: the seed reports {printed}, the model holds {expected}")
    return payload


def challenged_ledger() -> Ledger:
    """The recorded chain, run on to the first height a challenge is outstanding."""
    scenario, signatures = trace.chain_scenario()
    ledger = scenario.ledger
    end = ledger.height + CHALLENGE_SEARCH_HEIGHTS
    while not ledger.open_challenges():
        require(ledger.height < end, "no challenge appeared after the chain's end")
        run_quiet_heights(
            ledger, ledger.height + 1, fixture.timestamp_of_height,
            signatures.oracle)
    return ledger


def entry_kinds(ledger: Ledger) -> set[int]:
    return {key[0] for key in ledger.economy_entries()}


def check_refused(application: pathlib.Path, database: pathlib.Path,
                  genesis: pathlib.Path, snapshot: pathlib.Path,
                  message: str, subject: str) -> None:
    existed = database.exists()
    result = seed(application, database, genesis, snapshot)
    require(result.returncode != 0, f"{subject}: the seed was accepted")
    require(message in result.stderr,
            f"{subject}: refused for another reason: {result.stderr.strip()}")
    require(database.exists() == existed,
            f"{subject}: a refused seed changed what is at the path")
    if existed:
        return
    inspected = inspect(application, genesis, snapshot)
    require(inspected.returncode != 0 and message in inspected.stderr,
            f"{subject}: inspection did not refuse it the same way")


def check_refusals(application: pathlib.Path, directory: pathlib.Path,
                   payload: bytes) -> None:
    genesis = directory / "chain.genesis"
    unusable = "not a state this chain can be seeded with"
    tampered = bytearray(payload)
    tampered[len(tampered) // 2] ^= 0x01
    (directory / "tampered.snapshot").write_bytes(bytes(tampered))
    check_refused(
        application, directory / "tampered.sqlite", genesis,
        directory / "tampered.snapshot", unusable, "a tampered payload")
    check_refused(
        application, directory / "chain.sqlite", genesis,
        directory / "chain.snapshot", "already exists",
        "a seed onto an existing store")

    foreign = directory / "foreign.genesis"
    foreign.write_bytes(g.encode(
        replace(fixture.genesis(), network_id=fixture.NETWORK_ID + 1)))
    check_refused(
        application, directory / "foreign.sqlite", foreign,
        directory / "chain.snapshot", unusable,
        "the chain's state under another chain's genesis")

    # The payload carries its own build authority key, and a restore takes its
    # parameters from the genesis it is opened with (ADR 0109).
    other_build = directory / "build.genesis"
    other_build.write_bytes(g.encode(
        replace(fixture.genesis(), build_authority_key=bytes([0x4B]) * 32)))
    check_refused(
        application, directory / "build.sqlite", other_build,
        directory / "chain.snapshot", unusable,
        "the chain's state under another build authority key")

    (directory / "genesis.snapshot").write_bytes(
        encode(Ledger.from_genesis(fixture.genesis())))
    check_refused(
        application, directory / "genesis.sqlite", genesis,
        directory / "genesis.snapshot", unusable, "a height-zero payload")


def verify(application: pathlib.Path, directory: pathlib.Path) -> int:
    shutil.rmtree(directory, ignore_errors=True)
    directory.mkdir(parents=True)
    genesis_bytes = g.encode(fixture.genesis())

    restart, _ = trace.restart_scenario()
    check_seed(application, directory, "restart", restart.ledger, genesis_bytes)
    chain, _ = trace.chain_scenario()
    payload = check_seed(
        application, directory, "chain", chain.ledger, genesis_bytes)
    challenged = challenged_ledger()
    check_seed(application, directory, "challenged", challenged, genesis_bytes)
    cutoff = population.cutoff_run().ledger
    check_seed(application, directory, "cutoff", cutoff, genesis_bytes)

    carried = set().union(*(entry_kinds(ledger) for ledger in (
        restart.ledger, chain.ledger, challenged, cutoff)))
    written = {
        value for name, value in vars(c).items()
        if name.endswith("_ENTRY") and isinstance(value, int)
    }
    require(carried == written - UNREACHABLE_ENTRY_KINDS,
            f"the seeds carry entry kinds {sorted(carried)}, not every "
            f"writable kind of {sorted(written)}")
    require(c.LAUNCH_RETIREMENT_ENTRY in entry_kinds(cutoff),
            "the cutoff population did not retire the launch key")

    check_refusals(application, directory, payload)

    shutil.rmtree(directory, ignore_errors=True)
    print(
        "version-ten seed: passed (4 ledgers -- the restart run at height "
        f"{restart.ledger.height}, the chain at height {chain.ledger.height}, "
        f"a challenge outstanding at height {challenged.height}, and the cutoff "
        f"population at height {cutoff.height} -- each seeded a C++ store from a "
        "Python-encoded payload and reported the model's identity, height, "
        "stamp, and root, as inspection did before and after, "
        f"carrying all {len(carried)} writable entry kinds; 5 bad seeds refused "
        "with no file left behind, and the 4 bad payloads refused by "
        "inspection too)"
    )
    return 0


def main() -> int:
    if len(sys.argv) != 3:
        raise RuntimeError(
            "usage: version_ten_seed_test.py <protocol-application-v10> <directory>")
    return verify(pathlib.Path(sys.argv[1]).resolve(),
                  pathlib.Path(sys.argv[2]).resolve())


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"version-ten seed: failed: {error}", file=sys.stderr)
        raise SystemExit(1)

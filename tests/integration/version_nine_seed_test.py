#!/usr/bin/env python3

"""A model ledger, encoded in Python, seeds a C++ store (ADR 0096).

`protocol-application-v9 --seed` accepts a payload only through
`decode_snapshot_v9`'s three gates, and only if it re-encodes to exactly its own
octets. So each seed below checks two things at once. The model's state is one a
chain could hold. And `version_nine_snapshot.encode` writes the bytes the C++
encoder would.

**Four ledgers are seeded, chosen for what they carry.**

- The restart run is four contiguous blocks: identities, escrows, a seat, and
  a transfer.
- The settled chain has run past a month's settlement. It carries uptime
  records, assignment records, the recovery pool, the monthly figures, and a
  monthly claim.
- A seated chain is stopped at the first height with a challenge outstanding.
- The `economy-scenario-suite-v4` population is taken at window 200, for its
  referral balances and typed custody. Its uptime records were supplied to the
  prologue rather than written by challenges. The gates cannot tell the
  difference, and it is here to check the encoding, not a provenance.

Between them they carry every entry kind version nine writes. Kind 5, the
direct decision, is the exception, and no block can write it while kind 6
refuses every sender. The test requires that coverage instead of asserting it.
Each seed must print the model's chain identity, height, stamp, and root.

**Four seeds are refused, and a refusal must leave no file:**

- a payload with one octet changed;
- a seed onto an existing store;
- the same state under another chain's genesis;
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

from simulation.economy_transition_v6.trace import Signatures  # noqa: E402
from simulation.economy_transition_v9 import contract as c  # noqa: E402
from simulation.economy_transition_v9 import genesis as g  # noqa: E402
from simulation.economy_transition_v9 import trace  # noqa: E402
from simulation.economy_transition_v9.block import run_quiet_heights  # noqa: E402
from simulation.economy_transition_v9.ledger import Ledger  # noqa: E402
from simulation.scenarios import economy_population_v4 as population  # noqa: E402
from version_nine_snapshot import encode  # noqa: E402

# No block writes a direct decision while kind 6 refuses every sender.
UNREACHABLE_ENTRY_KINDS = {c.DIRECT_DECISION_ENTRY}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def seed(application: pathlib.Path, database: pathlib.Path,
         genesis: pathlib.Path, snapshot: pathlib.Path):
    return subprocess.run(
        [str(application), "--seed", str(database), str(genesis), str(snapshot)],
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
    result = seed(application, database, genesis, snapshot)
    require(result.returncode == 0,
            f"{name}: the seed was refused: {result.stderr.strip()}")
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
    """A seated chain at the first height a challenge is outstanding."""
    signatures = Signatures()
    scenario, _alice, _bob = trace._seated_chain(
        signatures, "challenged", trace.timestamp_of_height)
    ledger = scenario.ledger
    while not ledger.open_challenges():
        run_quiet_heights(
            ledger, ledger.height + 1, trace.timestamp_of_height,
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


def verify(application: pathlib.Path, directory: pathlib.Path) -> int:
    shutil.rmtree(directory, ignore_errors=True)
    directory.mkdir(parents=True)
    genesis_bytes = g.encode(trace.genesis())

    restart, _ = trace.restart_scenario()
    check_seed(application, directory, "restart", restart.ledger, genesis_bytes)
    settled, _ = trace.settled_scenario()
    payload = check_seed(
        application, directory, "settled", settled.ledger, genesis_bytes)
    challenged = challenged_ledger()
    check_seed(application, directory, "challenged", challenged, genesis_bytes)
    populated = population.PopulationRun(stop_window=200).run().ledger
    check_seed(application, directory, "population", populated,
               g.encode(population.genesis()))

    carried = set().union(*(entry_kinds(ledger) for ledger in (
        restart.ledger, settled.ledger, challenged, populated)))
    written = {
        value for name, value in vars(c).items()
        if name.endswith("_ENTRY") and isinstance(value, int)
    }
    require(carried == written - UNREACHABLE_ENTRY_KINDS,
            f"the seeds carry entry kinds {sorted(carried)}, not every "
            f"writable kind of {sorted(written)}")

    genesis = directory / "settled.genesis"
    tampered = bytearray(payload)
    tampered[len(tampered) // 2] ^= 0x01
    (directory / "tampered.snapshot").write_bytes(bytes(tampered))
    check_refused(
        application, directory / "tampered.sqlite", genesis,
        directory / "tampered.snapshot",
        "not a state this chain can be seeded with", "a tampered payload")
    check_refused(
        application, directory / "settled.sqlite", genesis,
        directory / "settled.snapshot",
        "already exists", "a seed onto an existing store")

    foreign = directory / "foreign.genesis"
    foreign.write_bytes(
        g.encode(replace(trace.genesis(), network_id=trace.NETWORK_ID + 1)))
    check_refused(
        application, directory / "foreign.sqlite", foreign,
        directory / "settled.snapshot",
        "not a state this chain can be seeded with",
        "the settled state under another chain's genesis")

    (directory / "genesis.snapshot").write_bytes(
        encode(Ledger.from_genesis(trace.genesis())))
    check_refused(
        application, directory / "genesis.sqlite", genesis,
        directory / "genesis.snapshot",
        "not a state this chain can be seeded with", "a height-zero payload")

    shutil.rmtree(directory, ignore_errors=True)
    print(
        "version-nine seed: passed (4 ledgers -- the restart run at height "
        f"{restart.ledger.height}, the settled chain at height "
        f"{settled.ledger.height}, a challenge outstanding at height "
        f"{challenged.height}, and the v4 population at height "
        f"{populated.height} -- each seeded a C++ store from a Python-encoded "
        "payload and reported the model's identity, height, stamp, and root, "
        f"carrying all {len(carried)} writable entry kinds; 4 bad seeds refused "
        "with no file left behind)"
    )
    return 0


def main() -> int:
    if len(sys.argv) != 3:
        raise RuntimeError(
            "usage: version_nine_seed_test.py <protocol-application-v9> <directory>")
    return verify(pathlib.Path(sys.argv[1]).resolve(),
                  pathlib.Path(sys.argv[2]).resolve())


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"version-nine seed: failed: {error}", file=sys.stderr)
        raise SystemExit(1)

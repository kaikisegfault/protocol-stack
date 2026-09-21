#!/usr/bin/env python3

"""The version-nine application as a process, with a real clock.

Everything below the binary has been exercised in C++ against the recorded
vectors, with a supplied clock. What has not is the **binary**: that it reads a
canonical version-nine genesis and refuses one that is not, that it prints the
figures a launcher needs — now three, because CometBFT's genesis gains
`genesis_time` — that it creates a database and reopens it, that it answers the
version-two wire on a private socket, and that it shuts down on SIGTERM.

**And that the clock it binds is the platform's.** The recorded chain's stamps
are January 2026. Against any real clock since, a proposal carrying the recorded
first-block stamp is *behind* the tolerance and one carrying a stamp in 2100 is
*ahead* of it — so the two decisions together place this process's clock between
them, which a stubbed, zero, or missing clock cannot do. `finalize_block` then
accepts the January stamp anyway, because C5 is `ProcessProposal`'s alone.

**The recorded blocks cannot be replayed here, and the reason is not a gap.**
The recorded run is signed under a stand-in verifier table, and this process
verifies with Ed25519, so the recorded transactions would be refused as results.
The block this suite finalizes is therefore **empty**, and what it checks about
it is what needs no recorded root: that two processes over the same genesis
agree on it, that one millisecond of stamp changes it, and that the stamp
survives a restart.
"""

import pathlib
import subprocess
import sys

import application_driver_v2 as driver

PROTOCOL_VERSION = 9
APP_STATE = b'"protocol-stack-v9"'
# magic, schema, chain id, height, timestamp: the previous state root starts here.
HEADER_PREVIOUS_ROOT_OFFSET = 4 + 2 + 32 + 8 + 8
# magic, schema, network id: the genesis stamp starts here.
GENESIS_TIMESTAMP_OFFSET = 4 + 2 + 4
MAX_TIMESTAMP_MILLIS = 253_402_300_799_999
# 2100-01-01T00:00:00Z, far enough ahead of any real clock that C5 must refuse it
# and well inside `calendar-v1`'s range.
YEAR_2100_MILLIS = 4_102_444_800_000


def load_values(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="ascii").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def identity(executable: pathlib.Path, genesis: pathlib.Path) -> dict[str, str] | None:
    result = subprocess.run(
        [str(executable), "--genesis-identity", str(genesis)],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return dict(
        line.split("=", 1) for line in result.stdout.decode("ascii").strip().splitlines()
    )


def with_stamp(genesis_bytes: bytes, stamp: int) -> bytes:
    offset = GENESIS_TIMESTAMP_OFFSET
    return genesis_bytes[:offset] + stamp.to_bytes(8, "big") + genesis_bytes[offset + 8 :]


def run_identity(executable, directory, genesis_path, genesis_bytes, expected) -> None:
    printed = identity(executable, genesis_path)
    if printed is None:
        raise RuntimeError("identity mode refused the canonical genesis")
    if printed != expected:
        raise RuntimeError(f"identity mode printed {printed}, expected {expected}")

    # **Validity reads no clock.** A stamp in the year 9999 is inside the range
    # and is a well-formed genesis for a chain that cannot start for eight
    # thousand years; one millisecond past the range is not a genesis at all.
    future = directory / "future.genesis"
    future.write_bytes(with_stamp(genesis_bytes, MAX_TIMESTAMP_MILLIS))
    printed = identity(executable, future)
    if printed is None:
        raise RuntimeError("a genesis inside the range was refused for its stamp")
    if printed["genesis_timestamp"] != str(MAX_TIMESTAMP_MILLIS):
        raise RuntimeError("identity mode printed a stamp the file does not carry")
    if printed["chain_id"] == expected["chain_id"]:
        raise RuntimeError("two genesis stamps produced one chain identity")

    # The schema version occupies the two octets after the four-octet magic, and
    # version eight's genesis is 142 octets: the width refusal and the validity
    # refusal are a pair, for the reason `headless_process_v8_test.py` records.
    cases = {
        "range.genesis": with_stamp(genesis_bytes, MAX_TIMESTAMP_MILLIS + 1),
        "short.genesis": bytes.fromhex("5053474e0009"),
        "empty.genesis": b"",
        "schema.genesis": genesis_bytes[:4] + bytes([0, 8]) + genesis_bytes[6:],
        "narrow.genesis": genesis_bytes[:142],
    }
    for name, content in cases.items():
        path = directory / name
        path.write_bytes(content)
        if identity(executable, path) is not None:
            raise RuntimeError(f"{name} was accepted as a genesis")


class Process:
    """One run of the binary against a home, stopped cleanly on exit."""

    def __init__(self, executable, database, genesis, socket_path) -> None:
        self._socket = socket_path
        self._process = driver.start(executable, database, genesis, socket_path)

    def __enter__(self) -> driver.Connection:
        try:
            self._connection = driver.Connection(self._socket)
        except Exception:
            driver.stop(self._process, self._socket)
            raise
        return self._connection

    def __exit__(self, *_: object) -> None:
        self._connection.close()
        driver.stop(self._process, self._socket)


def expect(value, wanted, subject: str) -> None:
    if value != wanted or type(value) is not type(wanted):
        raise RuntimeError(f"{subject}: expected {wanted!r}, got {value!r}")


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit("usage: headless_process_v9_test.py EXECUTABLE VECTORS DIRECTORY")
    executable = pathlib.Path(sys.argv[1]).resolve()
    values = load_values(pathlib.Path(sys.argv[2]))
    directory = pathlib.Path(sys.argv[3]).resolve()
    if directory.exists():
        for entry in sorted(directory.iterdir()):
            entry.unlink()
    directory.mkdir(parents=True, exist_ok=True)

    genesis_bytes = bytes.fromhex(values["genesis.bytes"])
    genesis_stamp = int(values["genesis.timestamp"])
    chain_id = bytes.fromhex(values["genesis.chain_id"])
    header = bytes.fromhex(values["restart.block0.header"])
    root = header[HEADER_PREVIOUS_ROOT_OFFSET : HEADER_PREVIOUS_ROOT_OFFSET + 32]
    january = int(values["restart.block0.timestamp"])
    genesis = directory / "g"
    genesis.write_bytes(genesis_bytes)
    socket_path = directory / "s"
    home = directory / "d"

    run_identity(executable, directory, genesis, genesis_bytes, {
        "chain_id": chain_id.hex().upper(),
        "app_hash": root.hex().upper(),
        "genesis_timestamp": str(genesis_stamp),
    })

    # A fresh process is at genesis, stamp included. A premature commit is a
    # status in a well-formed frame, and it latches, so it comes last.
    with Process(executable, home, genesis, socket_path) as connection:
        expect(connection.info(), driver.Info(PROTOCOL_VERSION, 0, genesis_stamp, root),
               "a fresh process")
        expect(connection.commit(), driver.Error.SEQUENCE_FAILURE, "a premature commit")
    if not home.exists():
        raise RuntimeError("the first run created no database")

    # InitChain compares the genesis stamp as a fourth value.
    with Process(executable, home, genesis, socket_path) as connection:
        expect(connection.init_chain(chain_id, 1, genesis_stamp + 1, APP_STATE),
               driver.Error.INVALID_REQUEST, "init_chain at a foreign genesis stamp")

    # **The real clock.** January is behind it, 2100 ahead of it, and neither is
    # a reason for FinalizeBlock to refuse a block the network decided.
    with Process(executable, home, genesis, socket_path) as connection:
        expect(connection.init_chain(chain_id, 1, genesis_stamp, APP_STATE), root,
               "init_chain")
        expect(connection.process_proposal(1, january),
               driver.Decision.TIMESTAMP_BEHIND_TOLERANCE, "a January proposal")
        expect(connection.process_proposal(1, YEAR_2100_MILLIS),
               driver.Decision.TIMESTAMP_AHEAD_OF_TOLERANCE, "a proposal in 2100")
        finalized = connection.finalize_block(1, january)
        if not isinstance(finalized, driver.Finalized) or finalized.results:
            raise RuntimeError(f"the empty January block was refused: {finalized!r}")
        committed = connection.commit()
        expect(committed, driver.Committed(1, january, finalized.state_root), "commit")

    # The stamp survives the process. A decided block below it is fatal and says
    # which rule failed.
    with Process(executable, home, genesis, socket_path) as connection:
        expect(connection.info(),
               driver.Info(PROTOCOL_VERSION, 1, january, committed.state_root),
               "a restarted process")
        expect(connection.finalize_block(2, january - 1),
               driver.TimestampFailure.DECIDED_BLOCK_FAILED_MONOTONICITY,
               "a decided block below the head's stamp")

    # **Two processes agree, and the stamp is in the root.** A second database
    # finalizes the same empty block to the same root, then refuses a fresh stamp
    # at the staged height; a third, given that fresh stamp, reaches another root.
    with Process(executable, directory / "d2", genesis, socket_path) as connection:
        expect(connection.init_chain(chain_id, 1, genesis_stamp, APP_STATE), root,
               "init_chain on a second database")
        again = connection.finalize_block(1, january)
        expect(again, finalized, "the same empty block on a second database")
        expect(connection.finalize_block(1, january + 1),
               driver.Error.SEQUENCE_FAILURE, "a fresh stamp at the staged height")
    with Process(executable, directory / "d3", genesis, socket_path) as connection:
        expect(connection.init_chain(chain_id, 1, genesis_stamp, APP_STATE), root,
               "init_chain on a third database")
        moved = connection.finalize_block(1, january + 1)
        if not isinstance(moved, driver.Finalized):
            raise RuntimeError(f"the moved stamp was refused: {moved!r}")
        if moved.state_root == finalized.state_root:
            raise RuntimeError("one millisecond of stamp did not change the root")

    for entry in sorted(directory.iterdir()):
        entry.unlink()
    print("version-nine headless process: passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

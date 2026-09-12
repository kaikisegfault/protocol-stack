#!/usr/bin/env python3

"""The version-eight application as a process.

Everything below this line has been exercised in C++ against the recorded
vectors. What has not is the **binary**: that it reads a canonical genesis file
and refuses one that is not canonical, that it prints the two figures an
operator has to put into a consensus engine's configuration, that it creates a
database on first run and reopens it on the second, that it answers the wire on
a private socket, and that it shuts down on SIGTERM and takes its socket with
it.

The figures it is checked against come from
`test-vectors/economy-transition-v8-execution.txt`, which knows nothing about
sockets or processes. **The genesis width is read out of that file too**, as
`genesis.prefix_bytes`, rather than written here: it is the one figure that
moved from version seven and a second copy of it is a second thing to forget.

The framing itself lives in `application_driver`, which
`driven_application_v8_test.py` speaks too. What is asked here is what a
*process* does; what is asked there is what a *replica* does with a block its
peers never proposed.
"""

import pathlib
import subprocess
import sys

import application_driver as driver

# The ledger version the process must report, and the application state a home
# is initialised with. Both are operator-visible and both moved with the
# version, so both are pinned here rather than derived from the binary.
PROTOCOL_VERSION = 8
APP_STATE = b'"protocol-stack-v8"'
MALFORMED_TRANSACTION = 1
# magic, schema, chain id, height: the header's previous state root starts here.
HEADER_PREVIOUS_ROOT_OFFSET = 4 + 2 + 32 + 8


def load_values(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="ascii").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def run_identity_mode(
    executable: pathlib.Path,
    genesis: pathlib.Path,
    chain_id: bytes,
    genesis_root: bytes,
) -> None:
    result = subprocess.run(
        [str(executable), "--genesis-identity", str(genesis)],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "identity mode failed: " + result.stderr.decode("utf-8", "replace")
        )
    printed = dict(
        line.split("=", 1)
        for line in result.stdout.decode("ascii").strip().splitlines()
    )
    if printed.get("chain_id") != chain_id.hex().upper():
        raise RuntimeError("identity mode printed a different chain identity")
    # The height-zero state root, which is what a consensus engine records as
    # the application hash before the first block. It is read out of a recorded
    # block header rather than restated here.
    if printed.get("app_hash") != genesis_root.hex().upper():
        raise RuntimeError("identity mode printed a different application hash")


def run_refusals(
    executable: pathlib.Path,
    directory: pathlib.Path,
    genesis_bytes: bytes,
    prefix_bytes: int,
) -> None:
    """A genesis file that is not canonical must not become a chain.

    The last two cases are the pair the moved width needs, and they are a pair
    on purpose. The **allocation bound** is already checked on the happy path:
    left at version seven's 110 it would refuse the canonical file and nothing
    would start. What no happy path checks is that the bound is *not* the
    validity rule, so one case is a file of exactly the right width that version
    eight would never have written, and one is a file of version seven's width.
    Deleting the bound admits the second; folding the validity rule into the
    bound admits the first.
    """
    if len(genesis_bytes) != prefix_bytes:
        raise RuntimeError("the recorded genesis is not the recorded width")
    # The schema version occupies the two octets after the four-octet magic.
    version_seven_schema = (
        genesis_bytes[:4] + bytes([0, 7]) + genesis_bytes[6:]
    )
    cases = {
        "short.genesis": bytes.fromhex("5053474e0008"),
        "empty.genesis": b"",
        "schema.genesis": version_seven_schema,
        "narrow.genesis": genesis_bytes[:110],
    }
    for name, content in cases.items():
        path = directory / name
        path.write_bytes(content)
        result = subprocess.run(
            [str(executable), "--genesis-identity", str(path)],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            raise RuntimeError(f"{name} was accepted as a genesis")


def run_first_process(
    executable: pathlib.Path,
    database: pathlib.Path,
    genesis: pathlib.Path,
    socket_path: pathlib.Path,
    genesis_root: bytes,
) -> None:
    process = driver.start(executable, database, genesis, socket_path)
    try:
        with driver.Connection(socket_path) as connection:
            info = connection.info()
            if not isinstance(info, driver.Info):
                raise RuntimeError(f"a fresh process refused info: {info!r}")
            if info.application_version != PROTOCOL_VERSION:
                raise RuntimeError("the process reports a foreign version")
            if info.height != 0:
                raise RuntimeError("a fresh process is not at height zero")
            if info.state_root != genesis_root:
                raise RuntimeError("the process reports a different genesis root")

            # Committing before the chain is initialised is a status in a
            # well-formed frame, not a broken connection.
            if connection.commit() is not driver.Error.SEQUENCE_FAILURE:
                raise RuntimeError("a premature commit was not refused")
    finally:
        driver.stop(process, socket_path)

    if not database.exists():
        raise RuntimeError("the first run created no database")


def run_second_process(
    executable: pathlib.Path,
    database: pathlib.Path,
    genesis: pathlib.Path,
    socket_path: pathlib.Path,
    chain_id: bytes,
    genesis_root: bytes,
) -> None:
    """A second run reopens what the first created and initialises the chain."""
    process = driver.start(executable, database, genesis, socket_path)
    try:
        with driver.Connection(socket_path) as connection:
            root = connection.init_chain(chain_id, 1, APP_STATE)
            if isinstance(root, driver.Error):
                raise RuntimeError(f"init_chain was refused: {root!r}")
            if root != genesis_root:
                raise RuntimeError("init_chain answered a different root")
            # An `Error` is an `IntEnum`, and `invalid_request` is 1 exactly as
            # the malformed-transaction admission code is, so the two are told
            # apart by type rather than by value.
            code = connection.check_transaction(bytes(8))
            if isinstance(code, driver.Error):
                raise RuntimeError(f"check_transaction was refused: {code!r}")
            if code != MALFORMED_TRANSACTION:
                raise RuntimeError("rubbish was not refused as malformed")
    finally:
        driver.stop(process, socket_path)


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: headless_process_v8_test.py EXECUTABLE VECTORS DIRECTORY"
        )
    executable = pathlib.Path(sys.argv[1]).resolve()
    values = load_values(pathlib.Path(sys.argv[2]))
    directory = pathlib.Path(sys.argv[3]).resolve()
    if directory.exists():
        for entry in sorted(directory.iterdir()):
            entry.unlink()
    directory.mkdir(parents=True, exist_ok=True)

    genesis_bytes = bytes.fromhex(values["genesis.bytes"])
    prefix_bytes = int(values["genesis.prefix_bytes"])
    chain_id = bytes.fromhex(values["genesis.chain_id"])
    header = bytes.fromhex(values["carried.block0.header"])
    genesis_root = header[
        HEADER_PREVIOUS_ROOT_OFFSET : HEADER_PREVIOUS_ROOT_OFFSET + 32
    ]

    genesis_path = directory / "g"
    genesis_path.write_bytes(genesis_bytes)
    database_path = directory / "d"
    socket_path = directory / "s"

    run_identity_mode(executable, genesis_path, chain_id, genesis_root)
    run_refusals(executable, directory, genesis_bytes, prefix_bytes)
    run_first_process(
        executable, database_path, genesis_path, socket_path, genesis_root
    )
    run_second_process(
        executable, database_path, genesis_path, socket_path, chain_id,
        genesis_root,
    )

    for entry in sorted(directory.iterdir()):
        entry.unlink()
    print("version-eight headless process: passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

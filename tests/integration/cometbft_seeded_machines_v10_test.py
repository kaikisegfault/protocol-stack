#!/usr/bin/env python3

"""Four version-ten replicas seeded past the assignment lag, and a machine
that registers a person.

This is M4.3n and requirement 3 of the M4 goal: **a registration is valid under
the key of an active, attested machine**, shown on a network. Every earlier
network registration was the launch key's. A network begun at genesis has no
active machine before height 86,400, which is days at the commit target.

**The script is `seeded_machines_v10`.** The model runs the history alone:
Alice and Bob each enroll, buy and activate a seat, and register its machine key
through kind 23, and only Alice's machine answers its audits. The head is block
86,400, which assigns window 1 and marks Alice's machine as having met it. Its
state is encoded as a version-ten snapshot, and
`protocol-cometbft-devnet start -seed` launches four replicas at 86,401.

**What the network must then show:**

- Its first block is 86,401, stamped with the seeded head's stamp.
- Alice's machine registers Carol, and the registration counts against Alice.
- Bob's machine, which met nothing, cannot register Dave: `MACHINE_NOT_ACTIVE`.
- The launch key still registers Erin, because one active machine is far below
  the hundred that retire it.
- Carol pays Alice, and Alice's kind-18 and kind-4 mints issue, and credit
  her, exactly what the script says they must. A second kind-4 mint is
  `NOTHING_TO_MINT`.
- Every receipt and root is the model's, each refusal lands on the root an
  empty block at that height and stamp would produce, and after a stop all four
  stores hold the model's height, stamp, and root and name protocol version 10.

The launch window is every seeded launch's (ADR 0097): one minute from the
head's stamp.
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
for _entry in (
    REPOSITORY,
    REPOSITORY / "tests" / "application",
    REPOSITORY / "tests" / "differential",
):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

import cometbft_four_validator_v10_test as four  # noqa: E402
import seeded_machines_v10 as script  # noqa: E402

from cometbft_devnet import Network, reserve_port_block, stop_network  # noqa: E402
from cometbft_rpc import committed_block  # noqa: E402
from pinned_sodium import Sodium  # noqa: E402
from version_ten_chain import FIXED_FEE, engine_millis  # noqa: E402


def require_first_block_carries_the_seed(chain: four.Chain, seeded: int) -> None:
    """The engine's first block is `H + 1`, stamped with the seeded head's stamp."""
    (seconds, nanos), count = committed_block(chain.rpc_port, seeded + 1)
    stamp = engine_millis(seconds, nanos)
    if count != 0 or nanos % 1_000_000 != 0 or stamp != chain.stamps[seeded]:
        raise RuntimeError(
            f"block {seeded + 1} is stamped {seconds}s {nanos}ns with {count} "
            f"transactions, not the seeded stamp {chain.stamps[seeded]} ms")


def run_step(
    network: Network, workspace: pathlib.Path, chain: four.Chain,
    step: script.Step,
) -> None:
    """Submit one step, and hold a mint to what it must issue and credit.

    The receipts already agree with the model's. These two figures are fixed
    in advance, so a model and a kernel that agreed on a wrong amount would
    still fail here. No empty block issues anything, so the supply's movement
    across the step is the mint's alone.
    """
    session = chain.session
    escrow = session.alice.escrow
    supply, balance = session.total_supply(), session.balance(escrow)
    if step.refusal is None:
        four.submit(network, workspace, chain, step.node, step.build)
    else:
        four.submit_refused(
            network, workspace, chain, step.node, step.build, step.code)
    if step.issues is not None:
        issued = session.total_supply() - supply
        if issued != step.issues:
            raise RuntimeError(
                f"{step.label} issued {issued} atomic units, not {step.issues}")
    if step.credits is not None:
        credited = session.balance(escrow) - balance + FIXED_FEE
        if credited != step.credits:
            raise RuntimeError(
                f"{step.label} credited alice {credited} atomic units, not "
                f"{step.credits}")


def verify(
    application: pathlib.Path,
    bridge: pathlib.Path,
    node: pathlib.Path,
    devnet: pathlib.Path,
    sodium_library: pathlib.Path,
    parent: pathlib.Path,
) -> None:
    sodium = Sodium(str(sodium_library))
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="cometbft-seeded-machines-v10-", dir=parent
    ) as temporary, tempfile.TemporaryDirectory(
        prefix="protocol-stack-machines-v10-sockets-"
    ) as socket_temporary:
        workspace = pathlib.Path(temporary)
        chain = four.Chain(sodium, script.genesis_stamp(four.now_millis()))
        machine = script.seed(chain, four.now_millis)
        script.check_the_history(chain.session, machine)
        seeded = chain.session.height
        steps = script.steps(chain.session)

        genesis = workspace / "protocol.genesis"
        genesis.write_bytes(chain.session.genesis)
        snapshot = workspace / "seed.snapshot"
        snapshot.write_bytes(chain.session.snapshot())

        network = Network(
            devnet, application, bridge, node,
            workspace / "network",
            pathlib.Path(socket_temporary) / "network",
            genesis, reserve_port_block(), four.PROTOCOL_VERSION,
            seed=snapshot,
        )
        chain.rpc_port = network.rpc_port(four.READER)

        process = four.start(network, workspace, chain, "the seeded launch")
        try:
            require_first_block_carries_the_seed(chain, seeded)
            for step in steps:
                run_step(network, workspace, chain, step)
            stop_network(process, network)
        finally:
            process.kill()
        four.audit(network, workspace, chain)
        script.check_what_the_network_did(chain.session)

    refusals = [step.refusal for step in steps if step.refusal]
    print(
        "CometBFT seeded-machines version-ten integration: passed (4 "
        f"independent replicas seeded at height {seeded}, where seat 0's "
        f"machine, which answered {len(machine.answered)} audits, is active "
        "and seat 1's is not; first block "
        f"{seeded + 1} stamped with the seeded head's stamp; a person "
        "registered by an active machine and counted against its founder, and "
        "one by the launch key; a transfer from the machine-registered person; "
        f"a kind-18 mint of {script.VERIFIED_USER_ISSUED} and a kind-4 mint of "
        f"{script.SEAT_ISSUED} atomic units; {len(refusals)} refusals by name "
        f"-- {', '.join(refusals)} -- each on the empty-block root; through "
        f"all 4 nodes to height {chain.session.height}, protocol version, "
        "durable height, stamp and root audited in all 4 stores)"
    )


def main() -> int:
    if len(sys.argv) != 7:
        raise RuntimeError(
            "usage: cometbft_seeded_machines_v10_test "
            "<application-v10> <bridge> <node> <devnet> "
            "<libsodium> <temporary-parent>"
        )
    paths = [pathlib.Path(value).resolve() for value in sys.argv[1:]]
    for executable in paths[:5]:
        if not executable.is_file():
            raise RuntimeError(f"missing integration input {executable}")
    verify(*paths)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(
            "CometBFT seeded-machines version-ten integration: failed: "
            f"{error}",
            file=sys.stderr,
        )
        raise SystemExit(1)

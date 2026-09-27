#!/usr/bin/env python3

"""A test Founder's lifecycle on four independent version-nine replicas.

This is requirement 1 of the M4 goal, `first-goal.md`. The version-nine kernel
has executed escrows, signers, and recovery against recorded vectors since
version six. Until this run no network had been asked for one: the
four-validator run registers, sells a seat, and transfers, and nothing more.

**The script is `founder_lifecycle_v9.lifecycle`**, eighteen blocks entering
through all four replicas in turn:

- Alice enrolls, buys a seat, and activates it.
- Her HUB key admits a second signer, creates a holding escrow, and funds it.
  The holding escrow gets a signer of its own and pays.
- The HUB key revokes her first signer and then her last, and each revoked key
  is refused by name.
- The HUB key recovers her with a new signer, which pays.

Two refusals are M4's exit criterion made concrete. Another person's HUB key,
and Alice's own signer presented as the authority, are both `UNAUTHORIZED` to
admit a signer: **no wallet key alone rewrites an identity.**

**The network is stopped and restarted twice**, and every store is audited after
each stop:

- once after the holding escrow is funded;
- once while Alice holds **no signer at all**.

So the recovery reads an identity with no signer back from SQLite, not from
memory. Every block's root and receipt must be the model's, and every refusal
must land on the root an empty block at that height and stamp would produce. The
launch and restart windows are the four-validator run's (ADR 0088, ADR 0089),
and so are the helpers that enforce them.
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

import cometbft_four_validator_v9_test as four  # noqa: E402

from cometbft_devnet import Network, reserve_port_block, stop_network  # noqa: E402
from founder_lifecycle_v9 import Step, lifecycle  # noqa: E402
from pinned_sodium import Sodium  # noqa: E402
from simulation.economy_transition_v6.identity import signer_id  # noqa: E402
from version_nine_chain import ALICE_ESCROW, ALICE_HOLDING_ESCROW  # noqa: E402


def segments(steps: tuple[Step, ...]) -> list[list[Step]]:
    """The script cut where it asks for a restart, one list per network run."""
    runs: list[list[Step]] = [[]]
    for step in steps:
        if step.restart_before and runs[-1]:
            runs.append([])
        runs[-1].append(step)
    return runs


def run_segment(
    network: Network, workspace: pathlib.Path, chain: four.Chain,
    steps: list[Step], what: str,
) -> None:
    process = four.start(network, workspace, chain, what)
    try:
        for step in steps:
            if step.refusal is None:
                four.submit(network, workspace, chain, step.node, step.raw)
            else:
                four.submit_refused(
                    network, workspace, chain, step.node, step.raw, step.code)
        stop_network(process, network)
    finally:
        process.kill()
    four.audit(network, workspace, chain)


def check_the_identity(chain: four.Chain) -> None:
    """What every replica now holds, read from the model they all agreed with."""
    session = chain.session
    if session.signers_of(ALICE_ESCROW) != {
        signer_id(session.alice_recovered_signer)
    }:
        raise RuntimeError("alice's first escrow does not hold the recovered signer")
    if session.signers_of(ALICE_HOLDING_ESCROW) != {
        signer_id(session.alice_holding_signer)
    }:
        raise RuntimeError("the holding escrow does not hold its own signer")
    if session.balance(ALICE_HOLDING_ESCROW) == 0:
        raise RuntimeError("the holding escrow was emptied")


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
        prefix="cometbft-founder-lifecycle-v9-", dir=parent
    ) as temporary, tempfile.TemporaryDirectory(
        prefix="protocol-stack-lifecycle-v9-sockets-"
    ) as socket_temporary:
        workspace = pathlib.Path(temporary)
        # Minted as late as the run allows, and every transaction signed before
        # the network starts: both spend the launch window otherwise.
        chain = four.Chain(sodium, four.now_millis())
        steps = lifecycle(chain.session)

        genesis = workspace / "protocol.genesis"
        genesis.write_bytes(chain.session.genesis)
        network = Network(
            devnet,
            application,
            bridge,
            node,
            workspace / "network",
            pathlib.Path(socket_temporary) / "network",
            genesis,
            reserve_port_block(),
            four.PROTOCOL_VERSION,
        )
        chain.rpc_port = network.rpc_port(four.READER)

        runs = segments(steps)
        for index, run in enumerate(runs):
            what = "the launch" if index == 0 else f"restart {index}"
            run_segment(network, workspace, chain, run, what)
        check_the_identity(chain)

    refusals = [step.refusal for step in steps if step.refusal]
    print(
        "CometBFT founder-lifecycle version-nine integration: passed "
        f"(4 independent replicas, {len(steps)} lifecycle transactions through "
        "all 4 nodes, a seat bought and activated, a second signer and a "
        "holding escrow added under the HUB key, every signer revoked, and the "
        "identity recovered under the HUB key after a restart with no signer; "
        f"{len(refusals)} refusals by name -- {', '.join(refusals)} -- each on "
        f"the empty-block root; {len(runs) - 1} full restarts inside the "
        "window, durable height, stamp and root audited in all 4 stores per "
        "stop)"
    )


def main() -> int:
    if len(sys.argv) != 7:
        raise RuntimeError(
            "usage: cometbft_founder_lifecycle_v9_test "
            "<application-v9> <bridge> <node> <devnet> "
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
            "CometBFT founder-lifecycle version-nine integration: "
            f"failed: {error}",
            file=sys.stderr,
        )
        raise SystemExit(1)

#!/usr/bin/env python3

"""A test Founder's lifecycle on four independent version-ten replicas.

This is requirement 1 of the M4 goal, `first-goal.md`, on the contract that
replaces version nine. Version ten's execution vectors reach kind 15 and none
of kinds 13, 14, or 16, so this run is also the first time the version-ten
kernel executes those three.

**The script is `founder_lifecycle_v10.lifecycle`**, twenty blocks entering
through all four replicas in turn:

- Alice enrolls, buys a seat, activates it, and keys its machine.
- Her HUB key admits a second signer, creates a holding escrow, and funds it.
  The holding escrow gets a signer of its own and pays.
- The HUB key revokes her first signer and then her last, and each revoked key
  is refused by name.
- The HUB key recovers her with a new signer, which pays.

Two refusals are M4's exit criterion made concrete. Another person's HUB key,
and Alice's own signer presented as the authority, are both `UNAUTHORIZED` to
admit a signer: **no wallet key alone rewrites an identity.** A third is
requirement 5's, on the action that needs it most: a recovery whose approval
would outlive its slot is `APPROVAL_LIFETIME_EXCEEDED`.

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

import cometbft_four_validator_v10_test as four  # noqa: E402

from cometbft_devnet import Network, reserve_port_block, stop_network  # noqa: E402
from founder_lifecycle_v10 import Step, check_the_identity, lifecycle  # noqa: E402
from pinned_sodium import Sodium  # noqa: E402


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
                four.submit(network, workspace, chain, step.node, step.build)
            else:
                four.submit_refused(
                    network, workspace, chain, step.node, step.build, step.code)
        stop_network(process, network)
    finally:
        process.kill()
    four.audit(network, workspace, chain)


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
        prefix="cometbft-founder-lifecycle-v10-", dir=parent
    ) as temporary, tempfile.TemporaryDirectory(
        prefix="protocol-stack-lifecycle-v10-sockets-"
    ) as socket_temporary:
        workspace = pathlib.Path(temporary)
        # Minted as late as the run allows: everything between here and the
        # network's first proposal spends the launch window.
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
        check_the_identity(chain.session)

    refusals = [step.refusal for step in steps if step.refusal]
    print(
        "CometBFT founder-lifecycle version-ten integration: passed "
        f"(4 independent replicas, {len(steps)} lifecycle transactions through "
        "all 4 nodes, a seat bought, activated, and keyed, a second signer and "
        "a holding escrow added under the HUB key, every signer revoked, and "
        "the identity recovered under the HUB key after a restart with no "
        f"signer; {len(refusals)} refusals by name -- {', '.join(refusals)} -- "
        f"each on the empty-block root; {len(runs) - 1} full restarts inside "
        "the window, protocol version, durable height, stamp and root audited "
        "in all 4 stores per stop)"
    )


def main() -> int:
    if len(sys.argv) != 7:
        raise RuntimeError(
            "usage: cometbft_founder_lifecycle_v10_test "
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
            "CometBFT founder-lifecycle version-ten integration: "
            f"failed: {error}",
            file=sys.stderr,
        )
        raise SystemExit(1)

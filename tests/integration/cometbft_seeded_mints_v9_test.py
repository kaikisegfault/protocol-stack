#!/usr/bin/env python3

"""Four version-nine replicas seeded past the assignment lag, and two mints.

This is M4.2c, the last of ADR 0096's three slices, and requirement 2 of the M4
goal: a kind-4 mint and a kind-18 mint execute on a network. No network in this
repository had minted before. A network begun at genesis reaches a kind-18 mint
at height 57,600 and a kind-4 mint at 86,400, which is days at the commit
target.

**The script is `seeded_mints_v9`.** The model runs the history alone: Alice
enrolls, buys seat 0, and activates it, and the seat's machine answers every
audit through windows 1 and 2. The head is block 86,400, which assigns window
1, stamped at the clock. Its state is encoded as a snapshot, and
`protocol-cometbft-devnet start -seed` launches four replicas at 86,401.

**What the network must then show:**

- Its first block is 86,401, stamped with the seeded head's stamp.
- Alice's kind-18 mint collects two daily permissions, and her kind-4 mint
  collects what seat 0 earned in window 1. Each receipt, issued amount
  included, and each root is the model's.
- A second mint of each kind is refused as `NOTHING_TO_MINT`, and Bob minting
  seat 0 is refused as `UNAUTHORIZED`. Each refusal lands on the root an empty
  block at that height and stamp would produce.
- After a stop, all four stores hold the model's height, stamp, and root.

The five transactions enter through all four replicas. The launch window is
every seeded launch's (ADR 0097): one minute from the head's stamp.
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
import cometbft_seeded_launch_v9_test as seeded_launch  # noqa: E402
import seeded_mints_v9 as script  # noqa: E402

from cometbft_devnet import Network, reserve_port_block, stop_network  # noqa: E402
from pinned_sodium import Sodium  # noqa: E402


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
        prefix="cometbft-seeded-mints-v9-", dir=parent
    ) as temporary, tempfile.TemporaryDirectory(
        prefix="protocol-stack-mints-v9-sockets-"
    ) as socket_temporary:
        workspace = pathlib.Path(temporary)
        chain = four.Chain(sodium, script.genesis_stamp(four.now_millis()))
        machine = script.seed(chain, four.now_millis)
        script.check_the_history(machine)
        seeded = chain.session.height
        steps = script.mints(chain.session)

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
            seeded_launch.require_first_block_carries_the_seed(chain, seeded)
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
        script.check_what_was_minted(chain.session)

    refusals = [step.refusal for step in steps if step.refusal]
    print(
        "CometBFT seeded-mints version-nine integration: passed (4 independent "
        f"replicas seeded at height {seeded}, past the assignment lag, from a "
        f"model history in which seat 0's machine answered "
        f"{len(machine.answered)} audits; first block {seeded + 1} stamped with "
        "the seeded head's stamp; a kind-18 mint of "
        f"{script.VERIFIED_USER_WINDOWS} daily permissions and a kind-4 mint of "
        f"window {script.AUDITED_WINDOW}, receipts and roots the model's; "
        f"{len(refusals)} refusals by name -- {', '.join(refusals)} -- each on "
        f"the empty-block root; through all 4 nodes to height "
        f"{chain.session.height}, durable height, stamp and root audited in "
        "all 4 stores)"
    )


def main() -> int:
    if len(sys.argv) != 7:
        raise RuntimeError(
            "usage: cometbft_seeded_mints_v9_test "
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
            f"CometBFT seeded-mints version-nine integration: failed: {error}",
            file=sys.stderr,
        )
        raise SystemExit(1)

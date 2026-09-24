from __future__ import annotations

import base64
import calendar
import json
import re
import urllib.request
from typing import Any

# A header time as CometBFT writes one: UTC, with between zero and nine
# fractional digits because Go's RFC 3339 nanosecond layout drops trailing
# zeros. Anything else is refused rather than guessed at.
_HEADER_TIME = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))?Z"
)


def rpc_call(port: int, method: str, params: dict[str, Any]) -> Any:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}",
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": "protocol-stack",
                "method": method,
                "params": params,
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        document = json.load(response)
    if "error" in document:
        raise RuntimeError(f"RPC {method} failed: {document['error']}")
    return document["result"]


def status(rpc_port: int) -> tuple[int, bytes]:
    sync = rpc_call(rpc_port, "status", {})["sync_info"]
    return (
        int(sync["latest_block_height"]),
        bytes.fromhex(sync["latest_app_hash"]),
    )


def abci_info(rpc_port: int) -> tuple[int, bytes]:
    response = rpc_call(rpc_port, "abci_info", {})["response"]
    return (
        int(response["last_block_height"]),
        base64.b64decode(response["last_block_app_hash"], validate=True),
    )


def commit_transaction(rpc_port: int, transaction: bytes) -> tuple[int, bytes]:
    """Broadcast, wait for the commit, and return its height and receipt.

    Both codes must be zero. The height and the receipt are returned rather
    than compared, because under version nine the receipt's block — and so the
    root that block produced — is only computable once the engine has said when
    it committed.
    """
    result = rpc_call(
        rpc_port,
        "broadcast_tx_commit",
        {"tx": base64.b64encode(transaction).decode("ascii")},
    )
    if int(result["check_tx"]["code"]) != 0:
        raise RuntimeError(f"CheckTx failed: {result['check_tx']}")
    if int(result["tx_result"]["code"]) != 0:
        raise RuntimeError(f"FinalizeBlock failed: {result['tx_result']}")
    return (
        int(result["height"]),
        base64.b64decode(result["tx_result"]["data"], validate=True),
    )


def broadcast(
    rpc_port: int,
    transaction: bytes,
    expected_height: int,
    expected_receipt: bytes,
) -> None:
    height, receipt = commit_transaction(rpc_port, transaction)
    if height != expected_height:
        raise RuntimeError("transaction committed at unexpected height")
    if receipt != expected_receipt:
        raise RuntimeError("ABCI receipt bytes differ from C++ model")


def parse_header_time(text: str) -> tuple[int, int]:
    """Seconds since the Unix epoch and nanoseconds, from a header's time.

    Parsed by hand because Python's own parser stops at microseconds, and the
    three digits it would drop are exactly the ones a truncation rule has to
    see to be checked.
    """
    match = _HEADER_TIME.fullmatch(text)
    if match is None:
        raise RuntimeError(f"unexpected header time {text!r}")
    year, month, day, hour, minute, second = (
        int(value) for value in match.groups()[:6]
    )
    seconds = calendar.timegm((year, month, day, hour, minute, second, 0, 0, 0))
    fraction = match.group(7) or ""
    return seconds, int(fraction.ljust(9, "0"))


def validator_address(rpc_port: int) -> bytes:
    """The validator address of the node serving this RPC port."""
    return bytes.fromhex(rpc_call(rpc_port, "status", {})["validator_info"]["address"])


def block_proposer(rpc_port: int, height: int) -> bytes:
    """The validator address that proposed the block committed at `height`."""
    header = rpc_call(rpc_port, "block", {"height": str(height)})["block"]["header"]
    if int(header["height"]) != height:
        raise RuntimeError(f"RPC returned height {header['height']} for {height}")
    return bytes.fromhex(header["proposer_address"])


def committed_block(rpc_port: int, height: int) -> tuple[tuple[int, int], int]:
    """A committed block's header time and how many transactions it holds."""
    block = rpc_call(rpc_port, "block", {"height": str(height)})["block"]
    header = block["header"]
    if int(header["height"]) != height:
        raise RuntimeError(f"RPC returned height {header['height']} for {height}")
    transactions = block["data"].get("txs") or []
    return parse_header_time(header["time"]), len(transactions)

from __future__ import annotations

import base64
import json
import urllib.request
from typing import Any


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


def broadcast(
    rpc_port: int,
    transaction: bytes,
    expected_height: int,
    expected_receipt: bytes,
) -> None:
    result = rpc_call(
        rpc_port,
        "broadcast_tx_commit",
        {"tx": base64.b64encode(transaction).decode("ascii")},
    )
    if int(result["height"]) != expected_height:
        raise RuntimeError("transaction committed at unexpected height")
    if int(result["check_tx"]["code"]) != 0:
        raise RuntimeError(f"CheckTx failed: {result['check_tx']}")
    if int(result["tx_result"]["code"]) != 0:
        raise RuntimeError(f"FinalizeBlock failed: {result['tx_result']}")
    if base64.b64decode(result["tx_result"]["data"]) != expected_receipt:
        raise RuntimeError("ABCI receipt bytes differ from C++ model")

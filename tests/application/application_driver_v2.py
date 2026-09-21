#!/usr/bin/env python3

"""A conversation with a running version-nine application process.

`protocol-application-v9` speaks the version-two frame. Version two differs from
version one in the frame's version octet, in three request payloads that carry a
timestamp, in four response payloads, and in two statuses. Everything else — the
header, the magic, the request identifiers, the process lifecycle, the three
block bounds, and the refusal-as-a-value rule — is `application_driver`'s, and is
imported rather than copied.

**Every answer is still a value.** A decision is a `Decision`, a statement about
this machine is an `Error`, and a decided block whose stamp this machine's rules
refuse is a `TimestampFailure`. A status `7` or `8` on any kind but a finalize is
not an answer at all: the contract makes the two reachable only from kind 6, so
this module treats one anywhere else as a malformed response and raises.
"""

from __future__ import annotations

import enum
import struct
from dataclasses import dataclass

import application_driver as v1
from application_driver import Disconnected, Error, Finalized, Kind, start, stop

__all__ = [
    "Committed",
    "Connection",
    "Decision",
    "Disconnected",
    "Error",
    "Finalized",
    "Info",
    "Kind",
    "TimestampFailure",
    "start",
    "stop",
]

WIRE_VERSION = 2


class Decision(enum.IntEnum):
    """`protocol::application::ProposalDecision`, answered under status zero."""

    ACCEPTED = 0
    HEIGHT_NOT_NEXT = 1
    TIMESTAMP_RANGE = 2
    TIMESTAMP_NOT_MONOTONIC = 3
    TIMESTAMP_AHEAD_OF_TOLERANCE = 4
    TIMESTAMP_BEHIND_TOLERANCE = 5
    RESOURCE_BOUND = 6
    NOT_EXECUTABLE = 7


class TimestampFailure(enum.IntEnum):
    """`protocol::application::TimestampFailureV9`, reachable only from kind 6."""

    DECIDED_BLOCK_FAILED_RANGE = 7
    DECIDED_BLOCK_FAILED_MONOTONICITY = 8


@dataclass(frozen=True)
class Info:
    application_version: int
    height: int
    timestamp: int
    state_root: bytes


@dataclass(frozen=True)
class Committed:
    height: int
    timestamp: int
    state_root: bytes


def _block_payload(
    height: int, timestamp: int, transactions: tuple[bytes, ...]
) -> bytes:
    encoded = struct.pack(">QQI", height, timestamp, len(transactions))
    return encoded + b"".join(v1._blob(entry) for entry in transactions)


class Connection(v1.Connection):
    """One version-two client connection."""

    wire_version = WIRE_VERSION

    def _answer(
        self, kind: Kind, payload: bytes = b""
    ) -> tuple[Error | TimestampFailure | None, bytes]:
        status, body = self.transact(kind, payload)
        if status == 0:
            return None, body
        v1._require(not body, "an error response carries no body")
        if status in TimestampFailure._value2member_map_:
            v1._require(
                kind == Kind.FINALIZE_BLOCK,
                f"status {status} answered kind {int(kind)}",
            )
            return TimestampFailure(status), body
        v1._require(1 <= status <= int(Error.INTERNAL_FAILURE), f"status {status}")
        return Error(status), body

    def info(self) -> Info | Error:
        error, body = self._answer(Kind.INFO)
        if error is not None:
            return error
        v1._require(len(body) == 56, "info body width")
        version, height, timestamp = struct.unpack(">QQQ", body[:24])
        return Info(version, height, timestamp, body[24:])

    def init_chain(
        self,
        chain_id: bytes,
        initial_height: int,
        genesis_timestamp: int,
        app_state: bytes,
    ) -> bytes | Error:
        payload = (
            chain_id
            + struct.pack(">QQ", initial_height, genesis_timestamp)
            + v1._blob(app_state)
        )
        error, body = self._answer(Kind.INIT_CHAIN, payload)
        if error is not None:
            return error
        v1._require(len(body) == 32, "init_chain body width")
        return body

    def process_proposal(
        self, height: int, timestamp: int, transactions: tuple[bytes, ...] = ()
    ) -> Decision | Error:
        error, body = self._answer(
            Kind.PROCESS_PROPOSAL, _block_payload(height, timestamp, transactions)
        )
        if error is not None:
            return error
        v1._require(
            len(body) == 1 and body[0] <= int(Decision.NOT_EXECUTABLE),
            "process_proposal decision",
        )
        return Decision(body[0])

    def finalize_block(
        self, height: int, timestamp: int, transactions: tuple[bytes, ...] = ()
    ) -> Finalized | Error | TimestampFailure:
        error, body = self._answer(
            Kind.FINALIZE_BLOCK, _block_payload(height, timestamp, transactions)
        )
        if error is not None:
            return error
        return v1._finalized(body)

    def commit(self) -> Committed | Error:
        error, body = self._answer(Kind.COMMIT)
        if error is not None:
            return error
        v1._require(len(body) == 48, "commit body width")
        height, timestamp = struct.unpack(">QQ", body[:16])
        return Committed(height, timestamp, body[16:])

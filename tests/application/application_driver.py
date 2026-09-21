#!/usr/bin/env python3

"""A conversation with a running version-eight application process.

`protocol-application-v8` speaks one private Unix socket and nothing else, so a
test that wants to ask it a question a consensus engine would ask has to speak
the wire. This module is that wire, and it is shared rather than copied: the
framing, the three block bounds, and the seven message kinds are one description
of the protocol, and a second copy of them beside a second test is a second
place for a figure to go stale.

**Every operation answers with a value rather than an exception.** A refusal is
the subject of the tests that use this, not an accident in them, so `Error`
comes back the way a success does and the caller decides which one it wanted.

**Two things are raised, and both are raised because they are not refusals.** A
response this module cannot decode is a defect in the application or in this
file, never an answer. And `Disconnected` is what a peer sees when the *wire*
refuses its frame: the server closes the connection without the application
ever being handed the request, which is a different event from a refusal and
must not be readable as one.
"""

from __future__ import annotations

import enum
import pathlib
import signal
import socket
import struct
import subprocess
import time
from dataclasses import dataclass

MAGIC = b"PSAP"
# The frame format's version: version one's for ledger versions one through
# eight. `application_driver_v2` speaks version two to version nine.
WIRE_VERSION = 1
HEADER = struct.Struct(">4sHBBQI")
REQUEST = 0
RESPONSE = 1
MAXIMUM_WIRE_PAYLOAD = 33_554_432

# The three block bounds. The wire decoder enforces all three before the
# application is handed anything, and the application holds the same three
# figures behind it; ADR 0072 records why a peer only ever meets the wire's copy.
MAXIMUM_BLOCK_INPUTS = 65_535
MAXIMUM_TRANSACTION_BYTES = 1_048_576
MAXIMUM_BLOCK_BYTES = 16_777_216


class Kind(enum.IntEnum):
    """`protocol::application::MessageKind`."""

    INFO = 1
    INIT_CHAIN = 2
    CHECK_TRANSACTION = 3
    PREPARE_PROPOSAL = 4
    PROCESS_PROPOSAL = 5
    FINALIZE_BLOCK = 6
    COMMIT = 7


class Error(enum.IntEnum):
    """`protocol::application::ApplicationError`, which any kind may answer."""

    INVALID_REQUEST = 1
    UNSUPPORTED = 2
    SEQUENCE_FAILURE = 3
    KERNEL_FAILURE = 4
    STORAGE_FAILURE = 5
    INTERNAL_FAILURE = 6


class Disconnected(RuntimeError):
    """The wire refused the frame and the server closed the connection."""


@dataclass(frozen=True)
class Info:
    application_version: int
    height: int
    state_root: bytes


@dataclass(frozen=True)
class Finalized:
    """A finalized block, and one `(code, receipt)` pair per raw input.

    The pairs are in the order the inputs arrived. A rejected admission carries
    its own small code and an empty receipt; every admitted transaction carries
    a receipt whether it succeeded or failed.
    """

    state_root: bytes
    block_id: bytes
    results: tuple[tuple[int, bytes], ...]


@dataclass(frozen=True)
class Committed:
    height: int
    state_root: bytes


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(f"malformed application response: {message}")


def _blob(payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + payload


def _block_payload(height: int, transactions: tuple[bytes, ...]) -> bytes:
    encoded = struct.pack(">QI", height, len(transactions))
    return encoded + b"".join(_blob(entry) for entry in transactions)


def _finalized(body: bytes) -> Finalized:
    """The finalize response body, whose layout both frame versions share."""
    _require(len(body) >= 68, "finalize_block prefix width")
    (count,) = struct.unpack(">I", body[64:68])
    results: list[tuple[int, bytes]] = []
    offset = 68
    for _ in range(count):
        _require(offset + 8 <= len(body), "finalize_block result header")
        code, length = struct.unpack(">II", body[offset : offset + 8])
        offset += 8
        _require(offset + length <= len(body), "finalize_block receipt")
        results.append((code, body[offset : offset + length]))
        offset += length
    _require(offset == len(body), "finalize_block trailing octets")
    return Finalized(body[:32], body[32:64], tuple(results))


class Connection:
    """One client connection, which carries the request identifiers.

    The server refuses a repeated request identifier on a connection, so the
    counter belongs here rather than to the process: a reconnect is a fresh
    conversation and starts over.
    """

    # The frame version this connection writes and requires back. A subclass
    # that speaks another version names it here and nowhere else.
    wire_version = WIRE_VERSION

    def __init__(self, socket_path: pathlib.Path, timeout: float = 10.0) -> None:
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.settimeout(timeout)
        self._socket.connect(str(socket_path))
        self._next_request_id = 1

    def __enter__(self) -> "Connection":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._socket.close()

    def _receive_exact(self, size: int) -> bytes:
        result = bytearray()
        while len(result) < size:
            chunk = self._socket.recv(size - len(result))
            if not chunk:
                raise Disconnected("the application closed the connection")
            result.extend(chunk)
        return bytes(result)

    def transact(self, kind: Kind, payload: bytes = b"") -> tuple[int, bytes]:
        """Send one request frame and return the response's status and body."""
        request_id = self._next_request_id
        self._next_request_id += 1
        frame = HEADER.pack(
            MAGIC, self.wire_version, REQUEST, int(kind), request_id, len(payload)
        )
        try:
            self._socket.sendall(frame + payload)
        except ConnectionError as error:
            # The server reads a bounded payload whole before it decodes, so a
            # frame the wire refuses is normally sent in full and answered with
            # a close. Losing the write instead is the same event seen earlier.
            raise Disconnected("the application closed the connection") from error
        header = self._receive_exact(HEADER.size)
        magic, version, direction, echoed_kind, echoed_id, length = HEADER.unpack(
            header
        )
        _require(magic == MAGIC, "frame magic")
        _require(version == self.wire_version, "frame version")
        _require(direction == RESPONSE, "frame direction")
        _require(echoed_kind == int(kind), "echoed message kind")
        _require(echoed_id == request_id, "echoed request identifier")
        _require(length <= MAXIMUM_WIRE_PAYLOAD, "payload size bound")
        body = self._receive_exact(length)
        _require(len(body) >= 6, "status prefix")
        status, reserved = struct.unpack(">HI", body[:6])
        _require(reserved == 0, "reserved field is not zero")
        return status, body[6:]

    def _answer(
        self, kind: Kind, payload: bytes = b""
    ) -> tuple[Error | None, bytes]:
        status, body = self.transact(kind, payload)
        if status == 0:
            return None, body
        _require(status <= int(Error.INTERNAL_FAILURE), f"status {status}")
        _require(not body, "an error response carries no body")
        return Error(status), body

    def info(self) -> Info | Error:
        error, body = self._answer(Kind.INFO)
        if error is not None:
            return error
        _require(len(body) == 48, "info body width")
        application_version, height = struct.unpack(">QQ", body[:16])
        return Info(application_version, height, body[16:])

    def init_chain(
        self, chain_id: bytes, initial_height: int, app_state: bytes
    ) -> bytes | Error:
        payload = chain_id + struct.pack(">Q", initial_height) + _blob(app_state)
        error, body = self._answer(Kind.INIT_CHAIN, payload)
        if error is not None:
            return error
        _require(len(body) == 32, "init_chain body width")
        return body

    def check_transaction(self, transaction: bytes) -> int | Error:
        error, body = self._answer(Kind.CHECK_TRANSACTION, _blob(transaction))
        if error is not None:
            return error
        _require(len(body) == 4, "check_transaction body width")
        return int(struct.unpack(">I", body)[0])

    def process_proposal(
        self, height: int, transactions: tuple[bytes, ...] = ()
    ) -> bool | Error:
        error, body = self._answer(
            Kind.PROCESS_PROPOSAL, _block_payload(height, transactions)
        )
        if error is not None:
            return error
        _require(len(body) == 1 and body[0] <= 1, "process_proposal body")
        return body[0] == 1

    def finalize_block(
        self, height: int, transactions: tuple[bytes, ...] = ()
    ) -> Finalized | Error:
        error, body = self._answer(
            Kind.FINALIZE_BLOCK, _block_payload(height, transactions)
        )
        if error is not None:
            return error
        return _finalized(body)

    def commit(self) -> Committed | Error:
        error, body = self._answer(Kind.COMMIT)
        if error is not None:
            return error
        _require(len(body) == 40, "commit body width")
        (height,) = struct.unpack(">Q", body[:8])
        return Committed(height, body[8:])


def await_socket(
    process: "subprocess.Popen[bytes]", socket_path: pathlib.Path
) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if socket_path.exists():
            probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                probe.connect(str(socket_path))
                return
            except (ConnectionRefusedError, FileNotFoundError):
                pass
            finally:
                probe.close()
        if process.poll() is not None:
            error = process.stderr.read().decode("utf-8", "replace")
            raise RuntimeError(f"application exited before ready: {error}")
        time.sleep(0.01)
    raise RuntimeError("application socket readiness timeout")


def start(
    executable: pathlib.Path,
    database: pathlib.Path,
    genesis: pathlib.Path,
    socket_path: pathlib.Path,
) -> "subprocess.Popen[bytes]":
    """Run the application against a home and wait until it answers."""
    if len(str(socket_path)) >= 100:
        raise RuntimeError("the socket pathname is too long for sun_path")
    process = subprocess.Popen(
        [str(executable), str(database), str(genesis), str(socket_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        await_socket(process, socket_path)
        if socket_path.stat().st_mode & 0o777 != 0o600:
            raise RuntimeError("application socket is not mode 0600")
        return process
    except Exception:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if process.stderr is not None:
            process.stderr.close()
        raise


def stop(process: "subprocess.Popen[bytes]", socket_path: pathlib.Path) -> None:
    """Ask for shutdown and require a clean exit that takes the socket with it."""
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            raise RuntimeError("application ignored SIGTERM")
    error = process.stderr.read().decode("utf-8", "replace")
    process.stderr.close()
    if process.returncode != 0:
        raise RuntimeError(f"application exit {process.returncode}: {error}")
    if socket_path.exists():
        raise RuntimeError("application retained socket after shutdown")

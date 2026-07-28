from __future__ import annotations

import pathlib
import socket
import struct
import subprocess
import time
import urllib.error
from dataclasses import dataclass
from typing import IO

from cometbft_rpc import rpc_call

HEADER = struct.Struct(">4sHBBQI")
INFO_KIND = 1
MAXIMUM_FRAME = 33_554_432


@dataclass
class ManagedProcess:
    name: str
    process: subprocess.Popen[bytes]
    log_path: pathlib.Path
    log_file: IO[bytes]

    def failure(self) -> RuntimeError:
        self.log_file.flush()
        output = self.log_path.read_text(encoding="utf-8", errors="replace")
        return RuntimeError(
            f"{self.name} exited {self.process.returncode}:\n{output}"
        )

    def stop(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
                raise RuntimeError(f"{self.name} ignored SIGTERM")
        if self.process.returncode != 0:
            raise self.failure()
        self.log_file.close()

    def kill(self) -> None:
        if self.process.poll() is None:
            self.process.kill()
            self.process.wait(timeout=5)
        if not self.log_file.closed:
            self.log_file.close()


def start_process(
    name: str,
    command: list[str | pathlib.Path],
    workspace: pathlib.Path,
) -> ManagedProcess:
    log_path = workspace / f"{name}.log"
    log_file = log_path.open("wb")
    process = subprocess.Popen(
        [str(value) for value in command],
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    return ManagedProcess(name, process, log_path, log_file)


def require_running(process: ManagedProcess) -> None:
    if process.process.poll() is not None:
        raise process.failure()


def reserve_ports(count: int) -> list[int]:
    reservations: list[socket.socket] = []
    try:
        for _ in range(count):
            reservation = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            reservation.bind(("127.0.0.1", 0))
            reservations.append(reservation)
        return [value.getsockname()[1] for value in reservations]
    finally:
        for reservation in reservations:
            reservation.close()


def await_unix_socket(
    process: ManagedProcess,
    path: pathlib.Path,
) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        require_running(process)
        if path.exists():
            probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                probe.connect(str(path))
                return
            except (ConnectionRefusedError, FileNotFoundError):
                pass
            finally:
                probe.close()
        time.sleep(0.02)
    raise RuntimeError("application socket readiness timeout")


def await_tcp(process: ManagedProcess, port: int) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        require_running(process)
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.02)
    raise RuntimeError(f"{process.name} TCP readiness timeout")


def await_health(process: ManagedProcess, rpc_port: int) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        require_running(process)
        try:
            if rpc_call(rpc_port, "health", {}) == {}:
                return
        except (OSError, urllib.error.URLError, ValueError):
            pass
        time.sleep(0.05)
    raise RuntimeError("CometBFT RPC health timeout")


def receive_exact(connection: socket.socket, size: int) -> bytes:
    result = bytearray()
    while len(result) < size:
        chunk = connection.recv(size - len(result))
        if not chunk:
            raise RuntimeError("unexpected application socket EOF")
        result.extend(chunk)
    return bytes(result)


def application_info(path: pathlib.Path) -> tuple[int, bytes]:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.connect(str(path))
        connection.sendall(HEADER.pack(b"PSAP", 1, 0, INFO_KIND, 1, 0))
        header = receive_exact(connection, HEADER.size)
        magic, version, direction, kind, request_id, size = HEADER.unpack(
            header
        )
        if (
            magic != b"PSAP"
            or version != 1
            or direction != 1
            or kind != INFO_KIND
            or request_id != 1
            or size > MAXIMUM_FRAME
        ):
            raise RuntimeError("invalid application Info response header")
        payload = receive_exact(connection, size)
    if len(payload) != 54 or payload[:6] != b"\0\0\0\0\0\0":
        raise RuntimeError("invalid application Info response")
    app_version, height = struct.unpack(">QQ", payload[6:22])
    if app_version != 1:
        raise RuntimeError("unexpected application version")
    return height, payload[22:]


def start_stack(
    application_binary: pathlib.Path,
    bridge_binary: pathlib.Path,
    node_binary: pathlib.Path,
    workspace: pathlib.Path,
    database: pathlib.Path,
    genesis: pathlib.Path,
    application_socket: pathlib.Path,
    home: pathlib.Path,
    abci_port: int,
    rpc_port: int,
) -> list[ManagedProcess]:
    processes: list[ManagedProcess] = []
    try:
        application = start_process(
            "application",
            [
                application_binary,
                database,
                genesis,
                application_socket,
            ],
            workspace,
        )
        processes.append(application)
        await_unix_socket(application, application_socket)

        bridge = start_process(
            "bridge",
            [
                bridge_binary,
                "-application-socket",
                application_socket,
                "-abci-listen",
                f"tcp://127.0.0.1:{abci_port}",
            ],
            workspace,
        )
        processes.append(bridge)
        await_tcp(bridge, abci_port)

        node = start_process(
            "cometbft",
            [node_binary, "start", "--home", home],
            workspace,
        )
        processes.append(node)
        await_health(node, rpc_port)
        return processes
    except Exception:
        for process in reversed(processes):
            process.kill()
        raise


def stop_stack(
    processes: list[ManagedProcess],
    application_socket: pathlib.Path,
) -> tuple[int, bytes]:
    node, bridge, application = processes[2], processes[1], processes[0]
    node.stop()
    bridge.stop()
    head = application_info(application_socket)
    application.stop()
    if application_socket.exists():
        raise RuntimeError("application retained its socket after shutdown")
    return head

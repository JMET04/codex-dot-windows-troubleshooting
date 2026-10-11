"""Compare TLS validation on two public hosts; never read or send credentials."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import socket
import ssl
import time


HOSTS = ("chatgpt.com", "codex-cloud-backend.chatgpt.com")
MAX_CONNECT_HEADER = 8192


class ConnectRejected(Exception):
    pass


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError
    return remaining


def _connect_proxy(sock: socket.socket, host: str, deadline: float) -> None:
    sock.settimeout(_remaining(deadline))
    sock.sendall(
        f"CONNECT {host}:443 HTTP/1.1\r\nHost: {host}:443\r\n\r\n".encode("ascii")
    )
    header = bytearray()
    while not header.endswith(b"\r\n\r\n"):
        if len(header) >= MAX_CONNECT_HEADER:
            raise ConnectRejected
        sock.settimeout(_remaining(deadline))
        byte = sock.recv(1)
        if not byte:
            raise ConnectRejected
        header.extend(byte)
    first_line = bytes(header).split(b"\r\n", 1)[0].split(b" ", 2)
    if len(first_line) < 2 or first_line[0] not in (b"HTTP/1.0", b"HTTP/1.1"):
        raise ConnectRejected
    if first_line[1] != b"200":
        raise ConnectRejected


def probe(host: str, proxy: tuple[str, int] | None, timeout: float) -> dict:
    if host not in HOSTS:
        raise ValueError("Only the two public diagnostic hosts are allowed")
    if proxy is not None and proxy[0] not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("Only a loopback proxy is allowed")
    result = {
        "host": host,
        "route": "configured_loopback_proxy" if proxy else "no_explicit_proxy",
        "tls_verified": False,
    }
    deadline = time.monotonic() + timeout
    try:
        # The OS resolver has its own timing. The deadline limits socket operations.
        with socket.create_connection(proxy or (host, 443), timeout=timeout) as raw:
            if proxy:
                _connect_proxy(raw, host, deadline)
            raw.settimeout(_remaining(deadline))
            context = ssl.create_default_context()
            # Keep both hostname verification and normal certificate trust required.
            with context.wrap_socket(raw, server_hostname=host):
                result["tls_verified"] = True
                # Do not send any application request after the TLS handshake.
    except ssl.SSLCertVerificationError as error:
        result["error_type"] = type(error).__name__
        result["certificate_verification_code"] = error.verify_code
        result["hostname_mismatch"] = error.verify_code == 62
    except Exception as error:
        # Exception messages, certificates and headers can contain private data.
        result["error_type"] = type(error).__name__
    return result


def write_report(path: Path, report: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proxy-host", choices=("127.0.0.1", "localhost", "::1"), default="127.0.0.1")
    parser.add_argument("--proxy-port", type=int, default=10808)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.proxy_port <= 65535 or not 0 < args.timeout <= 30:
        parser.error("Proxy port must be 1..65535 and timeout must be 0..30 seconds")
    if args.output and args.output.exists():
        parser.error("Output must be a new file; existing evidence is not overwritten")
    results = [
        probe(host, proxy, args.timeout)
        for host in HOSTS
        for proxy in (None, (args.proxy_host, args.proxy_port))
    ]
    report = {
        "recorded_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "read_only_network_diagnostic": True,
        "credentials_used": False,
        "tls_validation_disabled": False,
        "settings_changed": False,
        "computer_control_verified": False,
        "route_note": "No explicit proxy can still pass through an OS or upstream tunnel.",
        "results": results,
    }
    if args.output:
        write_report(args.output, report)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(item["tls_verified"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

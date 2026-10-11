"""Experimental, time-bounded opaque relay for one fixed public Dot hostname.

This does not modify hosts, install services, replay messages, read credentials,
terminate TLS, or establish that a Dot task executed successfully.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import signal


TARGET = "codex-cloud-backend.chatgpt.com"
TARGET_PORT = 443
LISTEN = "127.0.0.2"
LISTEN_PORT = 443
PROXY = "127.0.0.1"
MAX_CONNECTIONS = 4
CONNECT_SECONDS = 12
MAX_BYTES_PER_DIRECTION = 16 * 1024 * 1024


class SocksRejected(Exception):
    """The upstream did not establish the requested unauthenticated tunnel."""


async def open_upstream(proxy_port: int, timeout: float = CONNECT_SECONDS,
                        protocol: str = "socks5"):
    """Fixed-name proxy connection; close the socket on every failed path."""
    if (not 1 <= proxy_port <= 65535 or not 0 < timeout <= CONNECT_SECONDS
            or protocol not in ("socks5", "http")):
        raise ValueError("Invalid bounded loopback-proxy parameters")
    writer = None
    try:
        async with asyncio.timeout(timeout):
            reader, writer = await asyncio.open_connection(PROXY, proxy_port)
            if protocol == "http":
                writer.write((f"CONNECT {TARGET}:443 HTTP/1.1\r\n"
                              f"Host: {TARGET}:443\r\n\r\n").encode("ascii"))
                await writer.drain()
                header = bytearray()
                while not header.endswith(b"\r\n\r\n"):
                    if len(header) >= 8192:
                        raise SocksRejected
                    header.extend(await reader.readexactly(1))
                status = bytes(header).split(b"\r\n", 1)[0].split(b" ", 2)
                if (len(status) < 2 or status[0] not in (b"HTTP/1.0", b"HTTP/1.1")
                        or status[1] != b"200"):
                    raise SocksRejected
                return reader, writer
            writer.write(b"\x05\x01\x00")
            await writer.drain()
            if await reader.readexactly(2) != b"\x05\x00":
                raise SocksRejected
            hostname = TARGET.encode("ascii")
            writer.write(b"\x05\x01\x00\x03" + bytes([len(hostname)])
                         + hostname + TARGET_PORT.to_bytes(2, "big"))
            await writer.drain()
            head = await reader.readexactly(4)
            if head[:3] != b"\x05\x00\x00":
                raise SocksRejected
            if head[3] == 1:
                await reader.readexactly(4)
            elif head[3] == 4:
                await reader.readexactly(16)
            elif head[3] == 3:
                length = (await reader.readexactly(1))[0]
                if length == 0:
                    raise SocksRejected
                await reader.readexactly(length)
            else:
                raise SocksRejected
            await reader.readexactly(2)
            return reader, writer
    except BaseException:
        if writer is not None:
            writer.close()
            with contextlib.suppress(Exception, asyncio.CancelledError):
                await asyncio.wait_for(writer.wait_closed(), 1)
        raise


async def copy_opaque(reader, writer):
    total = 0
    while True:
        data = await reader.read(65536)
        if not data:
            return
        total += len(data)
        if total > MAX_BYTES_PER_DIRECTION:
            raise ConnectionError("Bounded byte limit exceeded")
        writer.write(data)
        await writer.drain()


class Relay:
    def __init__(self, proxy_port: int, protocol: str = "socks5"):
        self.proxy_port = proxy_port
        self.protocol = protocol
        self.tasks = set()
        self.stats = {"accepted": 0, "rejected_at_capacity": 0,
                      "upstream_connected": 0, "connection_errors": 0}

    def accepted(self, reader, writer):
        if len(self.tasks) >= MAX_CONNECTIONS:
            self.stats["rejected_at_capacity"] += 1
            writer.close()
            return
        self.stats["accepted"] += 1
        task = asyncio.create_task(self.handle(reader, writer))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def handle(self, reader, writer):
        upstream = None
        pumps = []
        try:
            remote_reader, upstream = await open_upstream(
                self.proxy_port, protocol=self.protocol)
            self.stats["upstream_connected"] += 1
            pumps = [asyncio.create_task(copy_opaque(reader, upstream)),
                     asyncio.create_task(copy_opaque(remote_reader, writer))]
            done, pending = await asyncio.wait(pumps, return_when=asyncio.FIRST_COMPLETED)
            for pump in done:
                pump.result()
        except asyncio.CancelledError:
            raise
        except Exception:
            # No exception messages, payloads, proxy replies or destination IPs.
            self.stats["connection_errors"] += 1
        finally:
            for pump in pumps:
                pump.cancel()
            if pumps:
                await asyncio.gather(*pumps, return_exceptions=True)
            for stream in (upstream, writer):
                if stream is not None:
                    stream.close()
                    with contextlib.suppress(Exception, asyncio.CancelledError):
                        await asyncio.wait_for(stream.wait_closed(), 1)

    async def close(self):
        pending = list(self.tasks)
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)


async def serve(proxy_port: int, seconds: int, protocol: str = "socks5"):
    relay = Relay(proxy_port, protocol)
    stopped = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(signum, stopped.set)
    server = await asyncio.start_server(relay.accepted, LISTEN, LISTEN_PORT)
    print(json.dumps({"state": "listening", "fixed_target": TARGET,
                      "maximum_lifetime_seconds": seconds,
                      "hosts_modified": False, "tls_terminated": False}), flush=True)
    try:
        async with server:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stopped.wait(), seconds)
    finally:
        server.close()
        await server.wait_closed()
        await relay.close()
        print(json.dumps({"state": "stopped", "stats": relay.stats,
                          "dot_control_verified": False}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proxy-port", required=True, type=int)
    parser.add_argument("--proxy-protocol", choices=("http", "socks5"),
                        default="socks5")
    parser.add_argument("--seconds", type=int, default=60)
    args = parser.parse_args()
    if not 1 <= args.proxy_port <= 65535 or not 5 <= args.seconds <= 180:
        parser.error("Proxy port must be 1..65535; lifetime must be 5..180 seconds")
    asyncio.run(serve(args.proxy_port, args.seconds, args.proxy_protocol))


if __name__ == "__main__":
    main()

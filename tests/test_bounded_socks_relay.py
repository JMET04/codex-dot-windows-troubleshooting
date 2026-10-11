"""Synthetic socket tests; these are not native Dot acceptance evidence."""

import asyncio
import contextlib
import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location(
    "bounded_socks_relay", Path(__file__).resolve().parents[1]
    / "scripts" / "bounded_socks_relay.py")
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)


class SocksTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.handlers = set()
        self.server = None

    async def asyncTearDown(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        for task in self.handlers:
            task.cancel()
        if self.handlers:
            await asyncio.gather(*self.handlers, return_exceptions=True)

    async def proxy(self, handler):
        def connected(reader, writer):
            task = asyncio.create_task(handler(reader, writer))
            self.handlers.add(task)
        self.server = await asyncio.start_server(connected, "127.0.0.1", 0)
        return self.server.sockets[0].getsockname()[1]

    async def test_remote_hostname_and_opaque_bytes(self):
        observed = []

        async def fake(reader, writer):
            try:
                observed.append(await reader.readexactly(3))
                writer.write(b"\x05\x00")
                await writer.drain()
                prefix = await reader.readexactly(5)
                target = await reader.readexactly(prefix[4] + 2)
                observed.append(prefix + target)
                writer.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
                await writer.drain()
                payload = await reader.readexactly(6)
                writer.write(payload)
                await writer.drain()
            finally:
                writer.close()
                await writer.wait_closed()

        port = await self.proxy(fake)
        reader, writer = await relay.open_upstream(port)
        writer.write(b"\x16\x03\x01abc")
        await writer.drain()
        self.assertEqual(await reader.readexactly(6), b"\x16\x03\x01abc")
        writer.close()
        await writer.wait_closed()
        target = relay.TARGET.encode("ascii")
        self.assertEqual(observed, [b"\x05\x01\x00", b"\x05\x01\x00\x03"
                                   + bytes([len(target)]) + target + b"\x01\xbb"])

    async def test_auth_required_rejected_and_socket_closed(self):
        closed = asyncio.Event()

        async def fake(reader, writer):
            try:
                await reader.readexactly(3)
                writer.write(b"\x05\x02")
                await writer.drain()
                self.assertEqual(await reader.read(), b"")
                closed.set()
            finally:
                writer.close()
                await writer.wait_closed()

        port = await self.proxy(fake)
        with self.assertRaises(relay.SocksRejected):
            await relay.open_upstream(port)
        await asyncio.wait_for(closed.wait(), 1)

    async def test_deadline_closes_half_open_proxy(self):
        closed = asyncio.Event()

        async def fake(reader, writer):
            try:
                await reader.readexactly(3)
                self.assertEqual(await reader.read(), b"")
                closed.set()
            finally:
                writer.close()
                await writer.wait_closed()

        port = await self.proxy(fake)
        with self.assertRaises(TimeoutError):
            await relay.open_upstream(port, timeout=0.05)
        await asyncio.wait_for(closed.wait(), 1)

    async def test_cancel_closes_half_open_proxy(self):
        connected = asyncio.Event()
        closed = asyncio.Event()

        async def fake(reader, writer):
            try:
                await reader.readexactly(3)
                connected.set()
                self.assertEqual(await reader.read(), b"")
                closed.set()
            finally:
                writer.close()
                await writer.wait_closed()

        port = await self.proxy(fake)
        task = asyncio.create_task(relay.open_upstream(port))
        await asyncio.wait_for(connected.wait(), 1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        await asyncio.wait_for(closed.wait(), 1)

    async def test_fixed_proxy_parameter_bounds(self):
        for port, timeout in [(0, 1), (65536, 1), (10808, 0), (10808, 13)]:
            with self.assertRaises(ValueError):
                await relay.open_upstream(port, timeout)

    async def test_http_connect_fixed_host_and_opaque_bytes(self):
        observed = []

        async def fake(reader, writer):
            try:
                observed.append(await reader.readuntil(b"\r\n\r\n"))
                writer.write(b"HTTP/1.1 200 OK\r\n\r\n")
                await writer.drain()
                writer.write(await reader.readexactly(6))
                await writer.drain()
            finally:
                writer.close()
                await writer.wait_closed()

        port = await self.proxy(fake)
        reader, writer = await relay.open_upstream(port, protocol="http")
        writer.write(b"\x16\x03\x01abc")
        await writer.drain()
        self.assertEqual(await reader.readexactly(6), b"\x16\x03\x01abc")
        writer.close()
        await writer.wait_closed()
        self.assertEqual(observed, [(f"CONNECT {relay.TARGET}:443 HTTP/1.1\r\n"
                                    f"Host: {relay.TARGET}:443\r\n\r\n").encode("ascii")])

    async def test_http_authentication_rejected_without_credentials(self):
        closed = asyncio.Event()

        async def fake(reader, writer):
            try:
                request = await reader.readuntil(b"\r\n\r\n")
                self.assertNotIn(b"Authorization", request)
                writer.write(b"HTTP/1.1 407 Proxy Authentication Required\r\n\r\n")
                await writer.drain()
                self.assertEqual(await reader.read(), b"")
                closed.set()
            finally:
                writer.close()
                await writer.wait_closed()

        port = await self.proxy(fake)
        with self.assertRaises(relay.SocksRejected):
            await relay.open_upstream(port, protocol="http")
        await asyncio.wait_for(closed.wait(), 1)


if __name__ == "__main__":
    unittest.main()

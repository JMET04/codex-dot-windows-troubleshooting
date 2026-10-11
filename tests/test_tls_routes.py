import importlib.util
import json
from pathlib import Path
import ssl
import tempfile
import time
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "probe_tls_routes.py"
SPEC = importlib.util.spec_from_file_location("tls_routes", SOURCE)
tls_routes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tls_routes)


class FakeSocket:
    def __init__(self, response=b"HTTP/1.1 200 Connection established\r\n\r\n"):
        self.response = bytearray(response)
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def settimeout(self, _):
        pass

    def sendall(self, data):
        self.sent.append(data)

    def recv(self, _):
        return bytes([self.response.pop(0)]) if self.response else b""


class TlsRoutesTests(unittest.TestCase):
    def test_certificate_rejection_has_no_retry_or_private_message(self):
        rejection = ssl.SSLCertVerificationError(1, "Bearer PRIVATE-TOKEN unrelated.private.host")
        rejection.verify_code = 62
        raw = FakeSocket()
        context = mock.Mock()
        context.wrap_socket.side_effect = rejection
        with mock.patch.object(tls_routes.socket, "create_connection", return_value=raw), \
                mock.patch.object(tls_routes.ssl, "create_default_context", return_value=context):
            report = tls_routes.probe("chatgpt.com", ("127.0.0.1", 10808), 8)
        self.assertFalse(report["tls_verified"])
        self.assertTrue(report["hostname_mismatch"])
        self.assertNotIn("PRIVATE", json.dumps(report))
        self.assertEqual(context.wrap_socket.call_count, 1)
        self.assertEqual(raw.sent, [b"CONNECT chatgpt.com:443 HTTP/1.1\r\nHost: chatgpt.com:443\r\n\r\n"])

    def test_default_tls_context_requires_normal_trust_and_hostname(self):
        real_context = ssl.create_default_context()
        self.assertEqual(real_context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(real_context.check_hostname)
        raw = FakeSocket()
        real_context.wrap_socket = mock.Mock(side_effect=ssl.SSLError("fixture failure"))
        with mock.patch.object(tls_routes.socket, "create_connection", return_value=raw), \
                mock.patch.object(tls_routes.ssl, "create_default_context", return_value=real_context):
            result = tls_routes.probe("chatgpt.com", None, 8)
        self.assertFalse(result["tls_verified"])
        self.assertEqual(real_context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(real_context.check_hostname)
        real_context.wrap_socket.assert_called_once_with(raw, server_hostname="chatgpt.com")
        self.assertEqual(raw.sent, [])

    def test_proxy_auth_and_malformed_success_are_rejected_before_tls(self):
        for first_line in (b"HTTP/1.1 407 Proxy Authentication Required", b"HTTP/1.1 2000 Fake"):
            raw = FakeSocket(first_line + b"\r\n\r\n")
            with self.subTest(first_line=first_line), \
                    mock.patch.object(tls_routes.socket, "create_connection", return_value=raw), \
                    mock.patch.object(tls_routes.ssl, "create_default_context") as make_context:
                result = tls_routes.probe("chatgpt.com", ("127.0.0.1", 10808), 8)
                self.assertEqual(result["error_type"], "ConnectRejected")
                make_context.assert_not_called()

    def test_proxy_header_limit_and_deadline(self):
        with self.assertRaises(tls_routes.ConnectRejected):
            tls_routes._connect_proxy(FakeSocket(b"x" * 9000), "chatgpt.com", time.monotonic() + 8)
        with self.assertRaises(TimeoutError):
            tls_routes._connect_proxy(FakeSocket(), "chatgpt.com", time.monotonic() - 1)

    def test_arbitrary_hosts_and_nonlocal_proxies_are_rejected(self):
        with self.assertRaises(ValueError):
            tls_routes.probe("private.example", None, 8)
        with self.assertRaises(ValueError):
            tls_routes.probe("chatgpt.com", ("proxy.example", 443), 8)

    def test_existing_evidence_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            tls_routes.write_report(path, {"first": True})
            with self.assertRaises(FileExistsError):
                tls_routes.write_report(path, {"first": False})
            self.assertEqual(json.loads(path.read_text()), {"first": True})


if __name__ == "__main__":
    unittest.main()

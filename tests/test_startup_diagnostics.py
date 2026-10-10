"""An actual early-exit subprocess must leave bounded, redacted diagnostics."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import probe_local_task as probe


class StartupDiagnosticsTests(unittest.TestCase):
    def test_early_exit_is_retained_without_credentials(self):
        real_popen = probe.subprocess.Popen
        fixture = (
            "import sys\n"
            "sys.stdin.readline()\n"
            "for i in range(40): print('ERROR fixture-'+str(i),file=sys.stderr)\n"
            "print('ERROR Authorization: Bearer fixture-secret',file=sys.stderr)\n"
            "print('ERROR access_token=fixture-token',file=sys.stderr)\n"
            "sys.exit(17)\n"
        )

        def start_fixture(args, **kwargs):
            return real_popen([sys.executable, "-c", fixture], **kwargs)

        with patch.object(probe, "resolve_codex", return_value=sys.executable), \
                patch.object(probe.subprocess, "Popen", side_effect=start_fixture):
            client = probe.ReadOnlyClient(None, timeout=5)
            try:
                with self.assertRaisesRegex(RuntimeError, "App-server ended"):
                    client.request("initialize", {"clientInfo": {"name": "fixture", "version": "1"}})
            finally:
                client.close()
            diagnostic = client.startup_diagnostics()
            self.assertEqual(diagnostic["exit_code"], 17)
            self.assertIn("fixture-39", diagnostic["stderr_tail"])
            self.assertNotIn("fixture-0\n", diagnostic["stderr_tail"])
            self.assertNotIn("fixture-secret", diagnostic["stderr_tail"])
            self.assertNotIn("fixture-token", diagnostic["stderr_tail"])
            self.assertLessEqual(len(diagnostic["stderr_tail"]), 2000)
            self.assertLessEqual(len(diagnostic["stderr_tail"].splitlines()), 12)

    def test_json_credentials_and_jwt_discard_entire_line(self):
        for value in ['ERROR {"refresh_token":"fixture"}', "ERROR eyJ" + "a" * 40]:
            self.assertEqual(probe.safe_diagnostic(value), "[redacted credential-bearing diagnostic]")
        self.assertEqual(probe.safe_diagnostic("ERROR file denied"), "ERROR file denied")


if __name__ == "__main__":
    unittest.main()

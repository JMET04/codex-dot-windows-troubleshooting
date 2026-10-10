"""Regressions for a desktop update removing its previous CLI directory."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "resolve_codex", Path(__file__).parents[1] / "scripts/resolve_codex.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DesktopUpdateTests(unittest.TestCase):
    def test_replacement_after_previous_runtime_is_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            old = base / "old-runtime/codex.exe"
            old.parent.mkdir()
            old.write_bytes(b"test fixture; never executed")
            self.assertEqual(module.resolve_codex(desktop_bin=base), str(old.resolve()))
            old.unlink()
            new = base / "replacement-runtime/codex.exe"
            new.parent.mkdir()
            new.write_bytes(b"test fixture; never executed")
            self.assertEqual(module.resolve_codex(desktop_bin=base), str(new.resolve()))

    def test_missing_explicit_path_does_not_silently_choose_another_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "removed/codex.exe"
            with self.assertRaises(FileNotFoundError):
                module.resolve_codex(executable=str(missing))


if __name__ == "__main__":
    unittest.main()

"""Locate the installed CLI without pinning a desktop update's cache directory."""
import os
import shutil
from pathlib import Path


def resolve_codex(executable=None, desktop_bin=None):
    if executable:
        requested = Path(executable).expanduser()
        if requested.is_file():
            return str(requested.resolve())
        located = shutil.which(str(executable))
        if located:
            return located
        raise FileNotFoundError("The explicitly requested Codex executable does not exist")

    if desktop_bin is not None or os.name == "nt":
        base = Path(desktop_bin) if desktop_bin is not None else (
            Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
            / "OpenAI/Codex/bin"
        )
        base = base.resolve()
        candidates = []
        for path in base.glob("*/codex.exe"):
            try:
                resolved = path.resolve(strict=True)
                resolved.relative_to(base)
                if resolved.is_file():
                    candidates.append(resolved)
            except (OSError, ValueError):
                continue
        if candidates:
            return str(max(candidates, key=lambda path: (path.stat().st_mtime_ns, str(path))))

    located = shutil.which("codex")
    if located:
        return located
    raise FileNotFoundError("No installed Codex CLI found; provide --codex with its current path")

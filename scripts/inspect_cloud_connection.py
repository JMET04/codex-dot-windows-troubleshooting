"""Read bounded desktop log tails; never connect, resume, or change settings.

The report contains only recognized event names, states, timestamps and counts.
Raw log text, account/device/thread identifiers and credentials are not copied.
"""
import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

MAX_FILES = 12
MAX_BYTES_PER_FILE = 256 * 1024
MAX_LINE_CHARS = 8192
FRESH_SECONDS = 120
STAMP = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z) ")
EVENT = re.compile(
    r"(?:info|warning|warn|error|debug) \[(?:AppServerConnection|electron-message-handler)\] "
    r"(app_server_connection\.(?:state_changed|websocket_error|"
    r"connection_failed_before_ready)|remote_connections\.connection_state_changed)(?:\s|$)"
)


def tail_lines(path):
    """Read a fixed byte budget and discard a leading partial line."""
    with path.open("rb") as handle:
        handle.seek(0, 2)
        size = handle.tell()
        start = max(0, size - MAX_BYTES_PER_FILE)
        handle.seek(start)
        data = handle.read(MAX_BYTES_PER_FILE)
    if start:
        _, separator, data = data.partition(b"\n")
        if not separator:
            return []
    if not data.endswith(b"\n"):
        data = data.rsplit(b"\n", 1)[0] if b"\n" in data else b""
    return [line for line in data.decode("utf-8", errors="replace").splitlines()
            if len(line) <= MAX_LINE_CHARS]


def parse_event(line):
    stamp = STAMP.match(line)
    if not stamp:
        return None
    event = EVENT.match(line[stamp.end():])
    if not event:
        return None
    if not re.search(r"\bhost(?:Id|Kind)=durable(?:\s|$)", line):
        return None
    try:
        occurred = datetime.fromisoformat(stamp[1].replace("Z", "+00:00"))
    except ValueError:
        return None
    name = event[1]
    state_key = "next" if name.endswith(".state_changed") else "state"
    if "connection_state_changed" in name:
        state_key = "state"
    state = re.search(r"\b" + state_key + r"=(ready|connecting|error|disconnected)(?:\s|$)", line)
    if state:
        kind = state[1]
    elif name.endswith((".websocket_error", ".connection_failed_before_ready")):
        kind = "error"
    else:
        return None
    http_403 = kind == "error" and "Unexpected server response: 403" in line
    # A ready event may still contain previousError=403; do not classify it as failure.
    return {"occurred": occurred, "state": kind, "http_403": http_403}


def summarize(lines, now):
    events = {}
    unavailable = set()
    for line in lines:
        if len(line) > MAX_LINE_CHARS:
            continue
        event = parse_event(line)
        if event:
            events[(event["occurred"], event["state"], event["http_403"])] = event
        stamp = STAMP.match(line)
        if (stamp and "[electron-message-handler] Request failed " in line
                and "failureReason=remote_unavailable" in line
                and "Codex app-server is not available" in line):
            try:
                unavailable.add(datetime.fromisoformat(stamp[1].replace("Z", "+00:00")))
            except ValueError:
                pass
    # Ignore future timestamps rather than reporting an event that has not occurred.
    ordered = sorted((event for event in events.values() if event["occurred"] <= now),
                     key=lambda event: (event["occurred"], event["state"] == "ready"))
    result = {"read_only": True, "includes_raw_logs": False,
              "computer_control_verified": False, "status": "no_cloud_evidence",
              "freshness_limit_seconds": FRESH_SECONDS}
    if not ordered:
        return result
    latest = ordered[-1]
    age = (now - latest["occurred"]).total_seconds()
    result["latest_event"] = {"timestamp": latest["occurred"].isoformat(),
                              "state": latest["state"], "http_403": latest["http_403"],
                              "age_seconds": round(age, 1)}
    if age > FRESH_SECONDS:
        result["status"] = "stale_cloud_evidence"
    elif latest["state"] == "ready":
        result["status"] = "ready_reported_requires_task_verification"
    elif latest["http_403"]:
        result["status"] = "cloud_websocket_http_403"
    else:
        result["status"] = "cloud_" + latest["state"]
    fresh_failures = [event for event in ordered if event["http_403"]
                      and 0 <= (now - event["occurred"]).total_seconds() <= FRESH_SECONDS]
    result["recent_403_event_count"] = len(fresh_failures)
    result["unavailable_timestamps_near_recent_403"] = sum(
        stamp <= now and any(abs((stamp - event["occurred"]).total_seconds()) <= 30
            for event in fresh_failures) for stamp in unavailable
    )
    result["correlation_note"] = "Time correlation does not establish the server's reason for rejection."
    return result


def inspect_logs(log_root, now):
    candidates = []
    for day in (now, now - timedelta(days=1)):
        directory = log_root / day.strftime("%Y/%m/%d")
        if directory.is_dir():
            candidates.extend(path for path in directory.glob("*.log") if path.is_file())
    files = sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)[:MAX_FILES]
    lines = []
    failures = 0
    for path in files:
        try:
            lines.extend(tail_lines(path))
        except OSError:
            failures += 1
    result = summarize(lines, now)
    result["files_examined"] = len(files)
    result["unreadable_files"] = failures
    result["max_bytes_per_file"] = MAX_BYTES_PER_FILE
    result["recorded_at"] = now.isoformat()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-root", type=Path,
                        help="Desktop Logs root containing UTC YYYY/MM/DD folders")
    parser.add_argument("--output", required=True, type=Path,
                        help="NEW local report path; existing files are refused")
    args = parser.parse_args(argv)
    root = args.log_root
    if root is None:
        local_data = os.environ.get("LOCALAPPDATA")
        if not local_data:
            parser.error("LOCALAPPDATA is unavailable; provide --log-root")
        root = Path(local_data) / "Codex" / "Logs"
    with args.output.open("x", encoding="utf-8") as report:
        result = inspect_logs(root, datetime.now(timezone.utc))
        json.dump(result, report, ensure_ascii=False, indent=2)
        report.write("\n")
    print(result["status"])
    print("Log state alone does not verify Dot task or computer control.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

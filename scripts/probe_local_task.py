"""Read one explicit local thread's metadata through official app-server stdio.
No chat contents, resume, turn/start, config writes, or permission overrides.
"""
import argparse
import json
import os
import queue
import subprocess
import threading
import time
from pathlib import Path


class ReadOnlyClient:
    def __init__(self, executable, timeout=25):
        self.timeout = timeout
        self.events = queue.Queue()
        self.request_id = 0
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self.proc = subprocess.Popen(
            [executable, "app-server"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
            creationflags=flags,
        )
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        for line in self.proc.stdout:
            try:
                self.events.put(json.loads(line))
            except json.JSONDecodeError:
                continue
        self.events.put({"transport_ended": True})

    def _write(self, obj):
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()

    def request(self, method, params):
        if method not in {"initialize", "thread/read", "thread/turns/list"}:
            raise ValueError("This probe supports metadata reads only")
        if method == "thread/turns/list" and (
            params.get("limit") != 1 or params.get("itemsView") != "notLoaded"
        ):
            raise ValueError("Only one latest turn without items is supported")
        self.request_id += 1
        request_id = self.request_id
        self._write({"id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(method + " timed out; inspect actual state")
            try:
                event = self.events.get(timeout=remaining)
            except queue.Empty:
                raise TimeoutError(method + " timed out; inspect actual state")
            if event.get("transport_ended"):
                raise RuntimeError("App-server ended before returning a result")
            if event.get("id") != request_id:
                continue
            if "error" in event:
                raise RuntimeError(json.dumps(event["error"], ensure_ascii=False))
            return event.get("result")

    def read_metadata(self, thread_id):
        self.request("initialize", {
            "clientInfo": {"name": "dot_readonly_probe", "version": "1.0.0"}
        })
        self._write({"method": "initialized"})
        response = self.request("thread/read", {
            "threadId": thread_id, "includeTurns": False
        })
        thread = response["thread"]
        return {key: thread.get(key) for key in
                ("id", "name", "cwd", "status", "createdAt", "updatedAt", "source")}

    def close(self):
        if self.proc.stdin:
            self.proc.stdin.close()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            # Only terminate the subprocess created by this probe.
            self.proc.terminate()
            self.proc.wait(timeout=5)
        self.proc.stdout.close()

    def read_latest_turn(self, thread_id):
        response = self.request("thread/turns/list", {
            "threadId": thread_id, "limit": 1,
            "sortDirection": "desc", "itemsView": "notLoaded",
        })
        return [{key: turn.get(key) for key in ("id", "status")}
                for turn in response.get("data", [])]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", default="codex",
                        help="Exact installed Codex CLI path, or codex from PATH")
    parser.add_argument("--thread", required=True,
                        help="A local thread explicitly authorized for reading")
    parser.add_argument("--output", required=True,
                        help="NEW private local report path; existing files are refused")
    parser.add_argument("--latest-turn", action="store_true",
                        help="Also read one latest turn ID/status without conversation items")
    args = parser.parse_args()
    output = Path(args.output)
    # Reserve a new report before starting the client; never overwrite evidence.
    with output.open("x", encoding="utf-8") as report:
        result = {"read_only": True, "includes_chat_content": False,
                  "transport": "official app-server stdio", "success": False}
        client = None
        try:
            client = ReadOnlyClient(args.codex)
            result["thread"] = client.read_metadata(args.thread)
            if args.latest_turn:
                result["latest_turn"] = client.read_latest_turn(args.thread)
            result["success"] = result["thread"]["id"] == args.thread
        except Exception as exc:
            result["error"] = str(exc)
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception as exc:
                    result["cleanup_error"] = str(exc)
            json.dump(result, report, ensure_ascii=False, indent=2)
            report.write("\n")
    print("Metadata probe succeeded." if result["success"] else
          "Metadata probe failed. Inspect the private local report.")
    print("Independent app-server loading state does not establish desktop idle state.")
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

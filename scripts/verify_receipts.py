"""Compare two local evidence reports. This does not authenticate their origin."""
import argparse
import json
from pathlib import Path


def verify(sender, target):
    control = sender.get("control", {})
    thread_id = sender.get("thread_id")
    turn_id = control.get("turn_id")
    nonce = control.get("nonce")
    if not isinstance(thread_id, str) or not thread_id:
        raise ValueError("Missing sender thread_id")
    if not isinstance(turn_id, str) or not turn_id:
        raise ValueError("Missing sender turn_id")
    if not isinstance(nonce, str) or not nonce:
        raise ValueError("Missing expected nonce")
    if sender.get("success") is not True:
        raise ValueError("Sender did not report success")
    if control.get("message_accepted") is not True or control.get("turn_completed") is not True:
        raise ValueError("Sender acceptance/completion is not verified")
    if control.get("turn_status") != "completed" or control.get("turn_error") is not None:
        raise ValueError("Sender turn failed or remains incomplete")
    if target.get("thread", {}).get("id") != thread_id:
        raise ValueError("Target thread does not match")
    turns = [turn for turn in target.get("turns", []) if turn.get("id") == turn_id]
    if len(turns) != 1:
        raise ValueError("Expected exactly one matching target turn")
    turn = turns[0]
    if turn.get("status") != "completed" or turn.get("error") is not None:
        raise ValueError("Target turn did not complete successfully")
    replies = [item.get("text", "") for item in turn.get("items", [])
               if item.get("type") == "agentMessage" and item.get("phase") == "final_answer"]
    if len(replies) != 1 or replies[0] != nonce or control.get("reply") != nonce:
        raise ValueError("Actual final reply does not match the exact nonce")
    return {"verified": True, "thread_matches": True, "turn_matches": True,
            "actual_final_reply_matches_exactly": True,
            "origin_authenticated_by_this_comparison": False,
            "synthetic": sender.get("data_kind") == "synthetic" or
                         target.get("data_kind") == "synthetic"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sender")
    parser.add_argument("target")
    args = parser.parse_args()
    try:
        result = verify(
            json.loads(Path(args.sender).read_text(encoding="utf-8-sig")),
            json.loads(Path(args.target).read_text(encoding="utf-8-sig")),
        )
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"verified": False, "error": str(exc)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

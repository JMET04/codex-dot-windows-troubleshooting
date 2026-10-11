"""Distinguish cloud transport failures from unrelated logs and stale UI labels."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import inspect_cloud_connection as inspect


class CloudConnectionTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 11, 0, 10, 40, tzinfo=timezone.utc)
        self.failure = ('2026-10-11T00:10:38.850Z info [AppServerConnection] '
                        'app_server_connection.state_changed cause=transport_closed '
                        'connectionError={"message":"Unexpected server response: 403"} '
                        'hostId=durable next=error previous=connecting')

    def test_failure_correlates_without_copying_log_content(self):
        unavailable = ('2026-10-11T00:10:38.867Z error [electron-message-handler] '
                       'Request failed conversationId=fixture-private-id '
                       'error={"message":"Codex app-server is not available"} '
                       'failureReason=remote_unavailable Authorization=fixture-secret')
        result = inspect.summarize([self.failure, self.failure, unavailable], self.now)
        self.assertEqual(result['status'], 'cloud_websocket_http_403')
        self.assertEqual(result['recent_403_event_count'], 1)
        self.assertEqual(result['unavailable_timestamps_near_recent_403'], 1)
        self.assertNotIn('fixture-', json.dumps(result))
        self.assertFalse(result['computer_control_verified'])

    def test_local_errors_and_chat_text_do_not_claim_cloud_failure(self):
        lines = [self.failure.replace('hostId=durable', 'hostId=local'),
                 self.failure.replace('[AppServerConnection]', '[chat-body]'),
                 '2026-10-11T00:10:38Z info chat body hostId=durable Unexpected server response: 403']
        self.assertEqual(inspect.summarize(lines, self.now)['status'], 'no_cloud_evidence')

    def test_newer_ready_overrides_old_403_and_retained_error_fields(self):
        ready = ('2026-10-11T00:10:39Z info [electron-message-handler] '
                 'remote_connections.connection_state_changed '
                 'previousError="Unexpected server response: 403" hostId=durable state=ready')
        result = inspect.summarize([ready, self.failure], self.now)
        self.assertEqual(result['status'], 'ready_reported_requires_task_verification')
        self.assertFalse(result['latest_event']['http_403'])
        self.assertFalse(result['computer_control_verified'])

    def test_stale_and_future_events_are_not_current_status(self):
        old = self.failure.replace('00:10:38.850Z', '00:00:38.850Z')
        future = self.failure.replace('00:10:38.850Z', '00:20:38.850Z')
        result = inspect.summarize([future, old], self.now)
        self.assertEqual(result['status'], 'stale_cloud_evidence')
        self.assertEqual(result['recent_403_event_count'], 0)

    def test_bounded_tails_and_exclusive_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = root / '2026' / '10' / '11'
            day.mkdir(parents=True)
            log = day / 'fixture.log'
            log.write_text('x' * (inspect.MAX_BYTES_PER_FILE + 100) + '\n' + self.failure + '\n')
            result = inspect.inspect_logs(root, self.now)
            self.assertEqual(result['status'], 'cloud_websocket_http_403')
            log.write_text(self.failure)  # An unfinished live log entry is not evidence.
            self.assertEqual(inspect.tail_lines(log), [])
            output = root / 'report.json'
            output.write_text('existing-evidence')
            with self.assertRaises(FileExistsError):
                inspect.main(['--log-root', str(root), '--output', str(output)])
            self.assertEqual(output.read_text(), 'existing-evidence')


if __name__ == '__main__':
    unittest.main()

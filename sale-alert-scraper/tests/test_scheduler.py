import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_due import run_due

class CollectorScheduleTests(unittest.TestCase):
    def test_throttle_and_retry_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("run_due.subprocess.run") as mock:
                mock.return_value.returncode = 0
                self.assertEqual(run_due(root, now=1000000), 0)
                self.assertEqual(run_due(root, now=1000000 + 10), 0)
                self.assertEqual(mock.call_count, 1)
                self.assertEqual(run_due(root, now=1000000 + 36 * 3600), 0)
                self.assertEqual(mock.call_count, 2)
            with sqlite3.connect(root / "storage" / "collector_schedule.sqlite") as db:
                self.assertEqual(db.execute("SELECT last_exit FROM collector_runs WHERE id=1").fetchone()[0], 0)

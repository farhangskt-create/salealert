import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from search_budget import reserve_search

class SearchBudgetTests(unittest.TestCase):
    def test_max_100_requests_and_reset_after_36_hours(self):
        with tempfile.TemporaryDirectory() as root:
            db = Path(root) / 'budget.sqlite'
            now = 10 * 86400
            self.assertTrue(all(reserve_search(db, now) for _ in range(100)))
            self.assertFalse(reserve_search(db, now))
            self.assertTrue(reserve_search(db, now + 36 * 3600 + 1))

if __name__ == '__main__':
    unittest.main()

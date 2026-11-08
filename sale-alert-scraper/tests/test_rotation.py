import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storage.smart_scheduler_db import SmartSchedulerDB
from search_budget import reserve_search

class RotationTests(unittest.TestCase):
    def test_persistent_category_rotation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / 'state.sqlite')
            db = SmartSchedulerDB(path)
            db.init_brands([{'id': 'a', 'category': 'Clothing', 'officialUrl': 'https://a.pk'},
                            {'id': 'b', 'category': 'Shoes', 'officialUrl': 'https://b.pk'}])
            first = db.next_category_batch(100000, 1)
            self.assertEqual(first[0]['category'], 'Clothing')
            restarted = SmartSchedulerDB(path)
            second = restarted.next_category_batch(100000, 1)
            self.assertEqual(second[0]['category'], 'Shoes')
            self.assertEqual(restarted.next_category_batch(100000, 1)[0]['category'], 'Clothing')

    def test_active_sale_preserved_on_empty_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SmartSchedulerDB(str(Path(tmp) / 'state.sqlite'))
            db.init_brands([{'id': 'a', 'category': 'Clothing', 'officialUrl': 'https://a.pk'}])
            import time
            expiry = int(time.time() * 1000) + 9000000
            db.update_brand_search_result('a', True, ['deal-1'], expiry, 1000)
            db.update_brand_search_result('a', False, [], 0, 1000)
            with db._get_connection() as conn:
                row = conn.execute('SELECT activeDealIds,dealExpiry FROM brand_search_history WHERE brandId=?', ('a',)).fetchone()
            self.assertEqual(row['activeDealIds'], '["deal-1"]')
            self.assertEqual(row['dealExpiry'], expiry)

    def test_budget_counts_only_explicit_reservations(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / 'budget.sqlite')
            import sqlite3
            self.assertTrue(reserve_search(db, now=100000))
            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM search_calls').fetchone()[0], 1)

if __name__ == '__main__': unittest.main()

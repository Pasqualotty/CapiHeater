"""Tests for core.scheduler"""

import json
import unittest
from datetime import date, timedelta

from core.scheduler import Scheduler


class TestScheduler(unittest.TestCase):

    def setUp(self):
        self.schedule_json = json.dumps([
            {"day": 1, "likes": 3, "follows": 0, "retweets": 0, "unfollows": 0},
            {"day": 2, "likes": 5, "follows": 1, "retweets": 0, "unfollows": 0},
            {"day": 3, "likes": 7, "follows": 2, "retweets": 1, "unfollows": 0},
        ])

    def test_day_number_today(self):
        s = Scheduler()
        today = date.today().isoformat()
        self.assertEqual(s.get_day_number(today), 1)

    def test_day_number_past(self):
        s = Scheduler()
        three_days_ago = (date.today() - timedelta(days=2)).isoformat()
        self.assertEqual(s.get_day_number(three_days_ago), 3)

    def test_get_today_actions_day1(self):
        s = Scheduler()
        today = date.today().isoformat()
        actions = s.get_today_actions(self.schedule_json, today)
        # With ±20% variation, likes should be roughly 3
        self.assertIn("likes", actions)
        self.assertGreaterEqual(actions["likes"], 1)
        self.assertLessEqual(actions["likes"], 5)

    def test_clamp_to_last_day(self):
        s = Scheduler()
        long_ago = (date.today() - timedelta(days=100)).isoformat()
        actions = s.get_today_actions(self.schedule_json, long_ago)
        # Should use day 3 (last day) values ± variation
        self.assertIn("likes", actions)
        self.assertGreaterEqual(actions["likes"], 4)


if __name__ == "__main__":
    unittest.main()

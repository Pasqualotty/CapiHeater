"""Unit tests for the comment_likes feature."""

import json
import sys
import os
import unittest

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.scheduler import Scheduler
from utils.config import COMMENT_LIKE_DELAY_MIN, COMMENT_LIKE_DELAY_MAX, MAX_COMMENT_LIKES_PER_DAY


class TestSchedulerCommentLikes(unittest.TestCase):
    """Test Scheduler handles comment_likes fields correctly."""

    def setUp(self):
        self.schedule = [
            {"day": 1, "likes": 5, "follows": 2, "retweets": 1, "unfollows": 0,
             "comment_likes": 0, "comment_likes_per_target": 2, "comment_like_skip_chance": 0.3},
            {"day": 5, "likes": 12, "follows": 4, "retweets": 2, "unfollows": 1,
             "comment_likes": 4, "comment_likes_per_target": 3, "comment_like_skip_chance": 0.25},
            {"day": 10, "likes": 22, "follows": 9, "retweets": 4, "unfollows": 3,
             "comment_likes": 6, "comment_likes_per_target": 3, "comment_like_skip_chance": 0.2},
        ]

    def test_comment_likes_in_actions(self):
        """comment_likes should be present in returned actions dict."""
        actions = Scheduler.get_today_actions(self.schedule, "2026-03-31")  # day 1
        self.assertIn("comment_likes", actions)
        self.assertIn("comment_likes_per_target", actions)
        self.assertIn("comment_like_skip_chance", actions)

    def test_comment_likes_zero_stays_zero(self):
        """comment_likes=0 should remain 0 after variation."""
        for _ in range(20):
            actions = Scheduler.get_today_actions(self.schedule, "2026-03-31")
            self.assertEqual(actions["comment_likes"], 0)

    def test_comment_likes_variation_applied(self):
        """comment_likes>0 should have +-20% variation."""
        values = set()
        for _ in range(50):
            actions = Scheduler.get_today_actions(self.schedule, "2026-03-27")  # day 5
            values.add(actions["comment_likes"])
            # Must be >= 1 (variation can't zero out positive base)
            self.assertGreaterEqual(actions["comment_likes"], 1)
        # With 50 runs, we should see at least some variation
        self.assertGreater(len(values), 1, "Expected variation in comment_likes")

    def test_comment_likes_per_target_no_variation(self):
        """comment_likes_per_target should NOT have variation applied."""
        for _ in range(20):
            actions = Scheduler.get_today_actions(self.schedule, "2026-03-27")
            self.assertEqual(actions["comment_likes_per_target"], 3)

    def test_comment_like_skip_chance_no_variation(self):
        """comment_like_skip_chance should NOT have variation applied."""
        for _ in range(20):
            actions = Scheduler.get_today_actions(self.schedule, "2026-03-27")
            self.assertAlmostEqual(actions["comment_like_skip_chance"], 0.25)

    def test_backward_compatibility_no_comment_likes_field(self):
        """Old schedules without comment_likes should default to 0."""
        old_schedule = [
            {"day": 1, "likes": 5, "follows": 2, "retweets": 1, "unfollows": 0},
        ]
        actions = Scheduler.get_today_actions(old_schedule, "2026-03-31")
        self.assertEqual(actions["comment_likes"], 0)
        self.assertEqual(actions["comment_likes_per_target"], 3)
        self.assertAlmostEqual(actions["comment_like_skip_chance"], 0.25)

    def test_empty_schedule_returns_comment_likes(self):
        """Empty schedule should still include comment_likes key."""
        actions = Scheduler.get_today_actions([], "2026-03-31")
        self.assertIn("comment_likes", actions)

    def test_json_string_schedule(self):
        """Schedule passed as JSON string should work."""
        json_str = json.dumps(self.schedule)
        actions = Scheduler.get_today_actions(json_str, "2026-03-27")
        self.assertIn("comment_likes", actions)
        self.assertGreaterEqual(actions["comment_likes"], 1)


class TestConfigConstants(unittest.TestCase):
    """Test new config constants exist and are reasonable."""

    def test_delay_constants_exist(self):
        self.assertIsInstance(COMMENT_LIKE_DELAY_MIN, float)
        self.assertIsInstance(COMMENT_LIKE_DELAY_MAX, float)
        self.assertIsInstance(MAX_COMMENT_LIKES_PER_DAY, int)

    def test_delay_range_valid(self):
        self.assertGreater(COMMENT_LIKE_DELAY_MAX, COMMENT_LIKE_DELAY_MIN)
        self.assertGreater(COMMENT_LIKE_DELAY_MIN, 0)

    def test_daily_cap_reasonable(self):
        self.assertGreater(MAX_COMMENT_LIKES_PER_DAY, 0)
        self.assertLessEqual(MAX_COMMENT_LIKES_PER_DAY, 200)


class TestDefaultScheduleJson(unittest.TestCase):
    """Test default_schedule.json has valid comment_likes fields."""

    def setUp(self):
        schedule_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "schedules", "default_schedule.json"
        )
        with open(schedule_path, "r", encoding="utf-8") as f:
            self.schedule = json.load(f)

    def test_all_days_have_comment_likes(self):
        for day in self.schedule:
            self.assertIn("comment_likes", day, f"Day {day['day']} missing comment_likes")
            self.assertIn("comment_likes_per_target", day, f"Day {day['day']} missing comment_likes_per_target")
            self.assertIn("comment_like_skip_chance", day, f"Day {day['day']} missing comment_like_skip_chance")

    def test_comment_likes_progression(self):
        """Comment likes should start at 0 and grow over time."""
        # Days 1-4 should be 0
        for day in self.schedule[:4]:
            self.assertEqual(day["comment_likes"], 0, f"Day {day['day']} should have 0 comment_likes")
        # Day 5+ should be > 0
        for day in self.schedule[4:]:
            self.assertGreater(day["comment_likes"], 0, f"Day {day['day']} should have comment_likes > 0")

    def test_skip_chance_range(self):
        for day in self.schedule:
            sc = day["comment_like_skip_chance"]
            self.assertGreaterEqual(sc, 0.0, f"Day {day['day']} skip_chance < 0")
            self.assertLessEqual(sc, 1.0, f"Day {day['day']} skip_chance > 1")

    def test_per_target_positive(self):
        for day in self.schedule:
            pt = day["comment_likes_per_target"]
            self.assertGreater(pt, 0, f"Day {day['day']} per_target should be > 0")


if __name__ == "__main__":
    unittest.main()

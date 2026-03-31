"""
Scheduler - Calculates daily actions based on a schedule and account start date.

The schedule_json is a list of day entries, e.g.:
[
    {"day": 1, "likes": 5,  "follows": 2,  "retweets": 1, "unfollows": 0},
    {"day": 2, "likes": 8,  "follows": 3,  "retweets": 2, "unfollows": 0},
    {"day": 3, "likes": 12, "follows": 5,  "retweets": 3, "unfollows": 1},
    ...
]

After the last scheduled day, the schedule maintains the last day's levels
indefinitely. A +-20% random variation is applied to all quantities.
"""

import json
import random
from datetime import date, datetime


class Scheduler:
    """Determines what actions an account should perform today."""

    VARIATION_PERCENT = 0.20

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_day_number(start_date) -> int:
        """Return which day of the schedule an account is on (1-indexed).

        Parameters
        ----------
        start_date : str | date | datetime
            The date the account started its warming schedule.

        Returns
        -------
        int
            Day number starting from 1.
        """
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        elif isinstance(start_date, datetime):
            start_date = start_date.date()

        today = date.today()
        delta = (today - start_date).days
        # Day 1 is the start date itself
        return max(1, delta + 1)

    @classmethod
    def get_schedule_length(cls, schedule_json) -> int:
        """Return the number of the last day defined in the schedule.

        Parameters
        ----------
        schedule_json : str | list
            The JSON schedule (string or already-parsed list).

        Returns
        -------
        int
            The last day number (e.g. 14 for a 14-day schedule, 1 for single-day).
        """
        schedule = cls._parse_schedule(schedule_json)
        if not schedule:
            return 1
        return schedule[-1].get("day", 1)

    # ------------------------------------------------------------------
    # Core method
    # ------------------------------------------------------------------

    @classmethod
    def get_today_actions(cls, schedule_json, start_date) -> dict:
        """Return today's action counts with random variation applied.

        Parameters
        ----------
        schedule_json : str | list
            The JSON schedule (string or already-parsed list).
        start_date : str | date | datetime
            Account start date.

        Returns
        -------
        dict
            ``{"likes": int, "follows": int, "retweets": int, "unfollows": int}``
        """
        schedule = cls._parse_schedule(schedule_json)
        if not schedule:
            return {"likes": 0, "follows": 0, "retweets": 0, "unfollows": 0,
                    "comment_likes": 0}

        day_number = cls.get_day_number(start_date)

        # Find the matching day entry, or clamp to the last day
        entry = cls._entry_for_day(schedule, day_number)

        # Apply +-20% random variation and ensure non-negative integers
        actions = {}
        for key in ("likes", "follows", "retweets", "unfollows", "comment_likes"):
            base = entry.get(key, 0)
            varied = cls._apply_variation(base)
            actions[key] = varied

        # Pass through browse settings (in seconds).
        # Auto-detect old schedules that used minutes (values < 30)
        # and convert them to seconds.
        for key in ("browse_before_min", "browse_before_max",
                     "browse_between_min", "browse_between_max"):
            val = entry.get(key, 0)
            if 0 < val < 30:
                # Likely stored in minutes (old format), convert to seconds
                val = val * 60
            actions[key] = val

        # Pass through behavior settings (no variation applied)
        # Use sensible defaults if the schedule was created before these fields existed
        actions["posts_to_open"] = entry.get("posts_to_open", 2)
        actions["view_comments_chance"] = entry.get("view_comments_chance", 0.3)
        actions["likes_on_feed"] = entry.get("likes_on_feed", False)
        actions["retweets_on_feed"] = entry.get("retweets_on_feed", False)
        actions["follow_initial_count"] = entry.get("follow_initial_count", 2)

        # Comment likes behavior settings (no variation applied)
        actions["comment_likes_per_target"] = entry.get("comment_likes_per_target", 3)
        actions["comment_like_skip_chance"] = entry.get("comment_like_skip_chance", 0.25)

        return actions

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    def _parse_schedule(cls, schedule_json):
        """Parse schedule_json into a sorted list of day entries."""
        if isinstance(schedule_json, str):
            schedule = json.loads(schedule_json)
        else:
            schedule = schedule_json

        if not isinstance(schedule, list) or len(schedule) == 0:
            return []

        # Sort by day number to be safe
        schedule.sort(key=lambda e: e.get("day", 0))
        return schedule

    @classmethod
    def _entry_for_day(cls, schedule: list, day_number: int) -> dict:
        """Return the schedule entry for *day_number*.

        If day_number exceeds the last defined day, the last entry is used
        (maintaining the final day's levels).
        """
        for entry in schedule:
            if entry.get("day") == day_number:
                return entry

        # Past the last defined day — use the last entry
        last_day = schedule[-1].get("day", 0)
        if day_number > last_day:
            return schedule[-1]

        # If the exact day isn't listed, find the nearest preceding entry
        best = schedule[0]
        for entry in schedule:
            if entry.get("day", 0) <= day_number:
                best = entry
            else:
                break
        return best

    @classmethod
    def _apply_variation(cls, base_value: int) -> int:
        """Apply +-20% random variation to *base_value*.

        If the base is > 0, the result is guaranteed to be at least 1
        (variation cannot zero out a scheduled action).
        """
        if base_value <= 0:
            return 0
        factor = 1.0 + random.uniform(-cls.VARIATION_PERCENT, cls.VARIATION_PERCENT)
        return max(1, round(base_value * factor))

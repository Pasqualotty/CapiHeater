"""Tests for workers.actions — basic import and instantiation checks."""

import unittest


class TestActionsImport(unittest.TestCase):

    def test_import_selectors(self):
        from workers.actions import selectors
        self.assertTrue(hasattr(selectors, "TWEET_ARTICLE"))

    def test_import_like_action(self):
        from workers.actions.like import LikeAction
        self.assertTrue(callable(LikeAction))

    def test_import_follow_action(self):
        from workers.actions.follow import FollowAction
        self.assertTrue(callable(FollowAction))

    def test_import_unfollow_action(self):
        from workers.actions.unfollow import UnfollowAction
        self.assertTrue(callable(UnfollowAction))

    def test_import_retweet_action(self):
        from workers.actions.retweet import RetweetAction
        self.assertTrue(callable(RetweetAction))


if __name__ == "__main__":
    unittest.main()

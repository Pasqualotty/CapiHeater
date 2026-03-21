"""
LikeAction - Scrolls the timeline and likes tweets
with human-like timing and behavior.
"""

import logging

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    ElementClickInterceptedException,
)

from workers.actions import selectors
from utils.humanizer import (
    gaussian_delay,
    random_delay,
    page_load_wait,
    scroll_pause,
    should_skip_action,
)

import random


class LikeAction:
    """Scroll the timeline and like tweets."""

    TIMELINE_URL = "https://x.com/home"

    def __init__(self, driver: WebDriver, logger: logging.Logger = None):
        self.driver = driver
        self.logger = logger or logging.getLogger(__name__)

    def execute(self, driver: WebDriver = None, target: int = 5) -> dict:
        """
        Like up to *target* tweets on the home timeline.

        Args:
            driver: Optional override driver (falls back to self.driver).
            target: Number of tweets to attempt to like.

        Returns:
            dict with keys 'success' (bool), 'liked' (int), 'errors' (int).
        """
        drv = driver or self.driver
        liked = 0
        errors = 0

        try:
            drv.get(self.TIMELINE_URL)
            page_load_wait()

            # Wait for the timeline to load
            WebDriverWait(drv, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selectors.TWEET_ARTICLE))
            )
        except TimeoutException:
            self.logger.error("Timeline did not load within timeout.")
            return {"success": False, "liked": 0, "errors": 1}

        seen_tweets: set = set()

        while liked < target:
            try:
                tweets = drv.find_elements(By.CSS_SELECTOR, selectors.TWEET_ARTICLE)
            except Exception:
                self.logger.warning("Could not fetch tweet elements.")
                break

            interacted = False
            for tweet in tweets:
                if liked >= target:
                    break

                # Use element id to avoid re-liking the same tweet
                try:
                    tweet_id = tweet.id
                except StaleElementReferenceException:
                    continue

                if tweet_id in seen_tweets:
                    continue
                seen_tweets.add(tweet_id)

                # Randomly skip some tweets to look natural
                if should_skip_action(skip_probability=0.3):
                    self.logger.debug("Skipping a tweet randomly.")
                    continue

                try:
                    like_btn = tweet.find_element(By.CSS_SELECTOR, selectors.LIKE_BUTTON)
                except (NoSuchElementException, StaleElementReferenceException):
                    # Already liked or element gone
                    continue

                try:
                    # Scroll tweet into view
                    drv.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        like_btn,
                    )
                    random_delay(0.5, 1.5)

                    like_btn.click()
                    liked += 1
                    self.logger.info("Liked tweet %d / %d", liked, target)
                    gaussian_delay()
                    interacted = True

                except (
                    StaleElementReferenceException,
                    ElementClickInterceptedException,
                ) as exc:
                    self.logger.debug("Click failed on like button: %s", exc)
                    errors += 1

            # Scroll down to load more tweets
            drv.execute_script(f"window.scrollBy(0, {random.randint(300, 800)});")
            scroll_pause()

            # Safety: if we went through all visible tweets without interacting,
            # scroll a bit more but stop if we still can't find new ones.
            if not interacted:
                drv.execute_script(f"window.scrollBy(0, {random.randint(300, 800)});")
                scroll_pause()
                new_tweets = drv.find_elements(By.CSS_SELECTOR, selectors.TWEET_ARTICLE)
                new_ids = {t.id for t in new_tweets if t.id not in seen_tweets}
                if not new_ids:
                    self.logger.info("No new tweets found after scrolling; stopping.")
                    break

        success = liked > 0
        self.logger.info("LikeAction complete: liked=%d, errors=%d", liked, errors)
        return {"success": success, "liked": liked, "errors": errors}

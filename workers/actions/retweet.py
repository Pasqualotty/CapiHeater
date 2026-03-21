"""
RetweetAction - Scrolls the timeline and retweets tweets
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


class RetweetAction:
    """Scroll the timeline and retweet tweets."""

    TIMELINE_URL = "https://x.com/home"

    def __init__(self, driver: WebDriver, logger: logging.Logger = None):
        self.driver = driver
        self.logger = logger or logging.getLogger(__name__)

    def execute(self, driver: WebDriver = None, target: int = 3) -> dict:
        """
        Retweet up to *target* tweets on the home timeline.

        Args:
            driver: Optional override driver (falls back to self.driver).
            target: Number of tweets to attempt to retweet.

        Returns:
            dict with keys 'success' (bool), 'retweeted' (int), 'errors' (int).
        """
        drv = driver or self.driver
        retweeted = 0
        errors = 0

        # --- Load timeline ---
        try:
            drv.get(self.TIMELINE_URL)
            page_load_wait()

            WebDriverWait(drv, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selectors.TWEET_ARTICLE))
            )
        except TimeoutException:
            self.logger.error("Timeline did not load within timeout.")
            return {"success": False, "retweeted": 0, "errors": 1}

        seen_tweets: set = set()

        while retweeted < target:
            try:
                tweets = drv.find_elements(By.CSS_SELECTOR, selectors.TWEET_ARTICLE)
            except Exception:
                self.logger.warning("Could not fetch tweet elements.")
                break

            interacted = False
            for tweet in tweets:
                if retweeted >= target:
                    break

                try:
                    tweet_id = tweet.id
                except StaleElementReferenceException:
                    continue

                if tweet_id in seen_tweets:
                    continue
                seen_tweets.add(tweet_id)

                # Randomly skip some tweets
                if should_skip_action(skip_probability=0.35):
                    self.logger.debug("Skipping a tweet randomly.")
                    continue

                # Skip if already retweeted (unretweet button present)
                try:
                    tweet.find_element(By.CSS_SELECTOR, selectors.UNRETWEET_BUTTON)
                    continue  # already retweeted
                except NoSuchElementException:
                    pass

                # Find the retweet button
                try:
                    rt_btn = tweet.find_element(By.CSS_SELECTOR, selectors.RETWEET_BUTTON)
                except (NoSuchElementException, StaleElementReferenceException):
                    continue

                try:
                    # Scroll into view
                    drv.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        rt_btn,
                    )
                    random_delay(0.5, 1.5)

                    # Click the retweet button to open the dropdown
                    rt_btn.click()
                    random_delay(0.3, 0.8)

                    # Click the "Repost" confirm option in the dropdown
                    confirm = WebDriverWait(drv, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selectors.RETWEET_CONFIRM))
                    )
                    random_delay(0.3, 0.8)
                    confirm.click()

                    retweeted += 1
                    self.logger.info("Retweeted tweet %d / %d", retweeted, target)
                    gaussian_delay()
                    interacted = True

                except TimeoutException:
                    self.logger.debug("Retweet confirm menu did not appear.")
                    errors += 1
                    # Press Escape to close any open menu
                    try:
                        from selenium.webdriver.common.keys import Keys
                        drv.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        random_delay(0.3, 0.8)
                    except Exception:
                        pass

                except (
                    StaleElementReferenceException,
                    ElementClickInterceptedException,
                ) as exc:
                    self.logger.debug("Retweet click failed: %s", exc)
                    errors += 1

            # Scroll for more tweets
            drv.execute_script(f"window.scrollBy(0, {random.randint(300, 800)});")
            scroll_pause()

            if not interacted:
                drv.execute_script(f"window.scrollBy(0, {random.randint(300, 800)});")
                scroll_pause()
                new_tweets = drv.find_elements(By.CSS_SELECTOR, selectors.TWEET_ARTICLE)
                new_ids = {t.id for t in new_tweets if t.id not in seen_tweets}
                if not new_ids:
                    self.logger.info("No new tweets found after scrolling; stopping.")
                    break

        success = retweeted > 0
        self.logger.info("RetweetAction complete: retweeted=%d, errors=%d", retweeted, errors)
        return {"success": success, "retweeted": retweeted, "errors": errors}

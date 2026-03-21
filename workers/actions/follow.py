"""
FollowAction - Navigate to a target user's profile and follow them.
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
from utils.humanizer import gaussian_delay, random_delay, page_load_wait


class FollowAction:
    """Follow a target Twitter/X user."""

    PROFILE_URL_TEMPLATE = "https://x.com/{username}"

    def __init__(self, driver: WebDriver, logger: logging.Logger = None):
        self.driver = driver
        self.logger = logger or logging.getLogger(__name__)

    def execute(self, driver: WebDriver = None, target: str = None) -> dict:
        """
        Follow the user specified by *target* (a username without @).

        Args:
            driver: Optional override driver (falls back to self.driver).
            target: Twitter/X username to follow (e.g. "elonmusk").

        Returns:
            dict with keys 'success' (bool) and 'message' (str).
        """
        drv = driver or self.driver

        if not target:
            self.logger.error("No target username provided for FollowAction.")
            return {"success": False, "message": "No target username provided."}

        username = target.lstrip("@")
        profile_url = self.PROFILE_URL_TEMPLATE.format(username=username)

        try:
            drv.get(profile_url)
            page_load_wait()

            # Wait for the profile page to load
            WebDriverWait(drv, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selectors.PROFILE_USER_NAME))
            )
        except TimeoutException:
            self.logger.error("Profile page did not load for @%s.", username)
            return {"success": False, "message": f"Profile page timeout for @{username}."}

        # Check if already following (unfollow button present means already following)
        try:
            drv.find_element(By.CSS_SELECTOR, selectors.PROFILE_UNFOLLOW_BUTTON)
            self.logger.info("Already following @%s.", username)
            return {"success": True, "message": f"Already following @{username}."}
        except NoSuchElementException:
            pass  # Not yet following, proceed

        # Locate and click the follow button
        try:
            follow_btn = WebDriverWait(drv, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selectors.PROFILE_FOLLOW_BUTTON))
            )
        except TimeoutException:
            self.logger.error("Follow button not found for @%s.", username)
            return {"success": False, "message": f"Follow button not found for @{username}."}

        try:
            random_delay(0.8, 2.0)
            follow_btn.click()
            page_load_wait()

            # Verify the follow went through by checking for the unfollow button
            try:
                WebDriverWait(drv, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selectors.PROFILE_UNFOLLOW_BUTTON))
                )
                self.logger.info("Successfully followed @%s.", username)
                return {"success": True, "message": f"Followed @{username}."}
            except TimeoutException:
                self.logger.warning("Follow click sent but could not verify for @%s.", username)
                return {"success": True, "message": f"Follow click sent for @{username} (unverified)."}

        except (
            StaleElementReferenceException,
            ElementClickInterceptedException,
        ) as exc:
            self.logger.error("Failed to click follow button for @%s: %s", username, exc)
            return {"success": False, "message": f"Click failed for @{username}: {exc}"}

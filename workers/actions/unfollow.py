"""
UnfollowAction - Navigate to a target user's profile and unfollow them,
handling the confirmation dialog.
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


class UnfollowAction:
    """Unfollow a target Twitter/X user."""

    PROFILE_URL_TEMPLATE = "https://x.com/{username}"

    def __init__(self, driver: WebDriver, logger: logging.Logger = None):
        self.driver = driver
        self.logger = logger or logging.getLogger(__name__)

    def execute(self, driver: WebDriver = None, target: str = None) -> dict:
        """
        Unfollow the user specified by *target* (a username without @).

        Args:
            driver: Optional override driver (falls back to self.driver).
            target: Twitter/X username to unfollow (e.g. "elonmusk").

        Returns:
            dict with keys 'success' (bool) and 'message' (str).
        """
        drv = driver or self.driver

        if not target:
            self.logger.error("No target username provided for UnfollowAction.")
            return {"success": False, "message": "No target username provided."}

        username = target.lstrip("@")
        profile_url = self.PROFILE_URL_TEMPLATE.format(username=username)

        # --- Navigate to profile ---
        try:
            drv.get(profile_url)
            page_load_wait()

            WebDriverWait(drv, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selectors.PROFILE_USER_NAME))
            )
        except TimeoutException:
            self.logger.error("Profile page did not load for @%s.", username)
            return {"success": False, "message": f"Profile page timeout for @{username}."}

        # --- Check if actually following ---
        try:
            unfollow_btn = drv.find_element(By.CSS_SELECTOR, selectors.PROFILE_UNFOLLOW_BUTTON)
        except NoSuchElementException:
            self.logger.info("Not following @%s; nothing to unfollow.", username)
            return {"success": True, "message": f"Not following @{username}."}

        # --- Click the unfollow button ---
        try:
            random_delay(0.8, 2.0)
            unfollow_btn.click()
            random_delay(0.3, 0.8)
        except (
            StaleElementReferenceException,
            ElementClickInterceptedException,
        ) as exc:
            self.logger.error("Failed to click unfollow for @%s: %s", username, exc)
            return {"success": False, "message": f"Click failed for @{username}: {exc}"}

        # --- Handle confirmation dialog ---
        try:
            confirm_btn = WebDriverWait(drv, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selectors.UNFOLLOW_CONFIRM))
            )
            random_delay(0.5, 1.2)
            confirm_btn.click()
            gaussian_delay()
        except TimeoutException:
            self.logger.warning(
                "No confirmation dialog appeared for @%s; unfollow may have completed directly.",
                username,
            )

        # --- Verify ---
        try:
            WebDriverWait(drv, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selectors.PROFILE_FOLLOW_BUTTON))
            )
            self.logger.info("Successfully unfollowed @%s.", username)
            return {"success": True, "message": f"Unfollowed @{username}."}
        except TimeoutException:
            self.logger.warning("Could not verify unfollow for @%s.", username)
            return {"success": True, "message": f"Unfollow sent for @{username} (unverified)."}

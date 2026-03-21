"""
BrowseFeedAction - Scrolls through the Twitter/X feed with natural,
human-like behavior.

Simulates realistic browsing: variable scroll speeds, snapping to tweet
boundaries, opening posts to read them, occasionally viewing comments,
and random micro-pauses that mimic a distracted human.
"""

import logging
import random
import time

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    NoSuchElementException,
    WebDriverException,
)

from workers.actions import selectors
from utils.humanizer import random_delay, scroll_pause, jitter


class BrowseFeedAction:
    """Scroll through the feed naturally for a configurable duration,
    optionally opening posts and viewing comments."""

    TIMELINE_URL = "https://x.com/home"

    # JS: find the tweet article closest to the vertical center of the
    # viewport and smooth-scroll it into view.
    _JS_SNAP_TO_NEAREST_TWEET = """
    const articles = document.querySelectorAll('article[data-testid="tweet"]');
    if (!articles.length) return null;
    const viewportCenter = window.innerHeight / 2;
    let closest = null;
    let minDist = Infinity;
    articles.forEach(a => {
        const rect = a.getBoundingClientRect();
        const articleCenter = rect.top + rect.height / 2;
        const dist = Math.abs(articleCenter - viewportCenter);
        if (dist < minDist) { minDist = dist; closest = a; }
    });
    if (closest) {
        closest.scrollIntoView({behavior: 'smooth', block: 'center'});
    }
    return closest ? true : false;
    """

    # JS: get basic info about the tweet currently closest to viewport center.
    _JS_GET_CENTER_TWEET_INFO = """
    const articles = document.querySelectorAll('article[data-testid="tweet"]');
    if (!articles.length) return null;
    const vc = window.innerHeight / 2;
    let closest = null;
    let minDist = Infinity;
    articles.forEach(a => {
        const rect = a.getBoundingClientRect();
        const center = rect.top + rect.height / 2;
        const dist = Math.abs(center - vc);
        if (dist < minDist) { minDist = dist; closest = a; }
    });
    if (!closest) return null;
    const rect = closest.getBoundingClientRect();
    const hasMedia = closest.querySelectorAll(
        'img[src*="pbs.twimg"], video, [data-testid="tweetPhoto"]'
    ).length > 0;
    const textEl = closest.querySelector('[data-testid="tweetText"]');
    const textLen = textEl ? textEl.textContent.length : 0;
    return {height: rect.height, hasMedia: hasMedia, textLength: textLen};
    """

    def __init__(self, driver: WebDriver, logger: logging.Logger = None):
        self.driver = driver
        self.logger = logger or logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def execute(
        self,
        driver: WebDriver = None,
        duration_minutes: float = 5.0,
        posts_to_open: int = 0,
        view_comments_chance: float = 0.3,
        stop_check=None,
    ) -> dict:
        """Browse the feed for *duration_minutes*.

        Parameters
        ----------
        driver : WebDriver, optional
            Override driver (falls back to self.driver).
        duration_minutes : float
            How many minutes to browse.
        posts_to_open : int
            Number of posts to click open, read, and navigate back from.
        view_comments_chance : float
            Probability (0-1) of scrolling through comments when a post
            is opened.
        stop_check : callable, optional
            A function that returns True when the worker should stop.

        Returns
        -------
        dict with keys: success, scrolls, posts_opened, duration_seconds.
        """
        drv = driver or self.driver
        scrolls = 0
        posts_opened = 0
        start = time.time()
        duration_secs = duration_minutes * 60

        self.logger.info(
            "Navegando pelo feed por %.1f minutos...", duration_minutes
        )

        # --- Navigate to timeline and wait for first tweets ---------------
        try:
            drv.get(self.TIMELINE_URL)
            random_delay(2.0, 4.0)

            WebDriverWait(drv, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, selectors.TWEET_ARTICLE)
                )
            )
        except TimeoutException:
            self.logger.warning("Timeline nao carregou durante browse.")
            return {
                "success": False,
                "scrolls": 0,
                "posts_opened": 0,
                "duration_seconds": 0,
            }

        # Determine roughly when to open posts (spread evenly across the
        # session so they don't all cluster at the start/end).
        open_at_scrolls = self._plan_post_opens(posts_to_open, duration_secs)

        # --- Main browsing loop -------------------------------------------
        while (time.time() - start) < duration_secs:
            if stop_check and stop_check():
                self.logger.info("Browse interrompido por sinal de parada.")
                break

            # Should we open a post on this iteration?
            if open_at_scrolls and scrolls >= open_at_scrolls[0]:
                open_at_scrolls.pop(0)
                if self._open_and_read_post(drv, view_comments_chance, stop_check):
                    posts_opened += 1

                # After returning from a post the feed may have shifted;
                # snap back to a tweet.
                self._snap_to_nearest_tweet(drv)
                if stop_check and stop_check():
                    break

            # Pick a browsing behaviour for this iteration.
            behaviour = random.choices(
                [
                    "scroll_small",
                    "scroll_medium",
                    "scroll_large",
                    "scroll_up",
                    "pause_read",
                    "distracted_pause",
                ],
                weights=[30, 25, 8, 7, 22, 8],
                k=1,
            )[0]

            if behaviour == "scroll_small":
                px = random.randint(150, 350)
                drv.execute_script(f"window.scrollBy(0, {px});")
                self._snap_to_nearest_tweet(drv)
                self._reading_pause(drv)

            elif behaviour == "scroll_medium":
                px = random.randint(400, 700)
                drv.execute_script(f"window.scrollBy(0, {px});")
                self._snap_to_nearest_tweet(drv)
                random_delay(1.5, 3.5)

            elif behaviour == "scroll_large":
                px = random.randint(750, 1200)
                drv.execute_script(f"window.scrollBy(0, {px});")
                self._snap_to_nearest_tweet(drv)
                random_delay(1.0, 2.0)

            elif behaviour == "scroll_up":
                px = random.randint(100, 400)
                drv.execute_script(f"window.scrollBy(0, -{px});")
                self._snap_to_nearest_tweet(drv)
                random_delay(2.0, 4.0)

            elif behaviour == "pause_read":
                # Linger on the current tweet as if reading it carefully.
                self._reading_pause(drv)

            elif behaviour == "distracted_pause":
                # Long pause — user got distracted.
                pause = random.uniform(12, 30)
                self.logger.debug("Pausa distraida de %.1fs", pause)
                time.sleep(pause)

            scrolls += 1

            # Occasionally hover over a tweet (mouse movement).
            if random.random() < 0.12:
                self._hover_random_tweet(drv)

        elapsed = time.time() - start
        self.logger.info(
            "Browse concluido: %d scrolls, %d posts abertos em %.0f segundos",
            scrolls,
            posts_opened,
            elapsed,
        )
        return {
            "success": True,
            "scrolls": scrolls,
            "posts_opened": posts_opened,
            "duration_seconds": round(elapsed),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _should_stop(self, stop_check) -> bool:
        return stop_check is not None and stop_check()

    def _snap_to_nearest_tweet(self, drv: WebDriver) -> None:
        """Smooth-scroll so the nearest tweet is centred on screen."""
        try:
            drv.execute_script(self._JS_SNAP_TO_NEAREST_TWEET)
            # Give the smooth scroll a moment to settle.
            time.sleep(random.uniform(0.3, 0.7))
        except WebDriverException:
            pass

    def _get_center_tweet_info(self, drv: WebDriver) -> dict | None:
        """Return {height, hasMedia, textLength} for the centred tweet."""
        try:
            return drv.execute_script(self._JS_GET_CENTER_TWEET_INFO)
        except WebDriverException:
            return None

    def _reading_pause(self, drv: WebDriver) -> None:
        """Pause proportionally to how 'big' the current tweet is."""
        info = self._get_center_tweet_info(drv)
        if info is None:
            random_delay(3.0, 8.0)
            return

        text_len = info.get("textLength", 0)
        has_media = info.get("hasMedia", False)

        # Base reading time scales with text length.
        if text_len < 50:
            base = random.uniform(3.0, 6.0)
        elif text_len < 200:
            base = random.uniform(5.0, 10.0)
        else:
            base = random.uniform(8.0, 15.0)

        # Media tweets get extra linger time.
        if has_media:
            base += random.uniform(2.0, 5.0)

        time.sleep(jitter(base, 0.2))

    def _hover_random_tweet(self, drv: WebDriver) -> None:
        """Move the mouse over a random visible tweet."""
        try:
            tweets = drv.find_elements(By.CSS_SELECTOR, selectors.TWEET_ARTICLE)
            if not tweets:
                return
            tweet = random.choice(tweets)
            ActionChains(drv).move_to_element(tweet).perform()
            random_delay(0.5, 2.0)
        except (StaleElementReferenceException, WebDriverException):
            pass

    # ------------------------------------------------------------------
    # Opening and reading individual posts
    # ------------------------------------------------------------------

    def _plan_post_opens(self, posts_to_open: int, duration_secs: float) -> list[int]:
        """Return a sorted list of scroll-iteration numbers at which to
        open a post.  Spread roughly evenly across the session."""
        if posts_to_open <= 0:
            return []

        # Estimate total scroll iterations (~8-12 seconds per iteration avg).
        est_iterations = max(int(duration_secs / 10), posts_to_open + 1)
        # Space them out, with jitter.
        interval = est_iterations / (posts_to_open + 1)
        targets = []
        for i in range(1, posts_to_open + 1):
            base = int(interval * i)
            jittered = max(1, base + random.randint(-2, 2))
            targets.append(jittered)
        return sorted(set(targets))

    def _open_and_read_post(
        self, drv: WebDriver, view_comments_chance: float, stop_check
    ) -> bool:
        """Click the centre tweet to open the full post view, read it,
        optionally scroll through comments, then navigate back.

        Returns True if the post was successfully opened and read.
        """
        try:
            # Find the tweet closest to the viewport centre.
            tweets = drv.find_elements(By.CSS_SELECTOR, selectors.TWEET_ARTICLE)
            if not tweets:
                return False

            # Pick the one nearest the centre.
            target = self._find_center_tweet_element(drv, tweets)
            if target is None:
                return False

            # Click on the tweet text or timestamp to navigate to the post.
            clickable = self._get_clickable_in_tweet(target)
            if clickable is None:
                return False

            self.logger.debug("Abrindo post para leitura...")
            ActionChains(drv).move_to_element(clickable).pause(
                random.uniform(0.3, 0.8)
            ).click().perform()

            # Wait for the post page to load (URL changes to /status/).
            try:
                WebDriverWait(drv, 10).until(
                    lambda d: "/status/" in d.current_url
                )
            except TimeoutException:
                self.logger.debug("Nao conseguiu abrir o post, voltando.")
                return False

            random_delay(1.5, 3.0)

            # "Read" the opened post.
            read_time = random.uniform(5, 20)
            self.logger.debug("Lendo post por %.1fs...", read_time)
            time.sleep(read_time)

            # Optionally scroll through comments.
            if random.random() < view_comments_chance:
                self._view_comments(drv, stop_check)

            # Navigate back to the feed.
            drv.back()
            random_delay(1.5, 3.5)

            # Wait for timeline to reappear.
            try:
                WebDriverWait(drv, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, selectors.TWEET_ARTICLE)
                    )
                )
            except TimeoutException:
                self.logger.debug("Timeline nao reapareceu apos voltar.")

            random_delay(1.0, 2.5)
            return True

        except (
            StaleElementReferenceException,
            NoSuchElementException,
            WebDriverException,
        ) as exc:
            self.logger.debug("Erro ao abrir post: %s", exc)
            # Try to get back to the feed if we navigated away.
            try:
                if "/status/" in drv.current_url:
                    drv.back()
                    random_delay(1.5, 3.0)
            except WebDriverException:
                pass
            return False

    def _find_center_tweet_element(self, drv: WebDriver, tweets):
        """Return the tweet WebElement closest to the viewport centre."""
        try:
            best = None
            best_dist = float("inf")
            vp_center = drv.execute_script("return window.innerHeight / 2;")
            for tweet in tweets:
                try:
                    rect = drv.execute_script(
                        "var r = arguments[0].getBoundingClientRect();"
                        "return {top: r.top, height: r.height};",
                        tweet,
                    )
                    center = rect["top"] + rect["height"] / 2
                    dist = abs(center - vp_center)
                    if dist < best_dist:
                        best_dist = dist
                        best = tweet
                except StaleElementReferenceException:
                    continue
            return best
        except WebDriverException:
            return None

    def _get_clickable_in_tweet(self, tweet):
        """Find a clickable element inside a tweet to open the post detail.
        Prefers the timestamp link (always present), falls back to tweet text.
        """
        # Timestamp link (e.g. "2h", "Mar 15") is an <a> with href containing /status/.
        try:
            links = tweet.find_elements(By.CSS_SELECTOR, "a[href*='/status/'] time")
            if links:
                # Click the parent <a> of the <time> element.
                return links[0].find_element(By.XPATH, "..")
        except (NoSuchElementException, StaleElementReferenceException):
            pass

        # Fallback: tweet text element.
        try:
            text_el = tweet.find_element(
                By.CSS_SELECTOR, '[data-testid="tweetText"]'
            )
            return text_el
        except (NoSuchElementException, StaleElementReferenceException):
            pass

        return None

    def _view_comments(self, drv: WebDriver, stop_check) -> None:
        """Scroll down the post view to read a few comments/replies."""
        num_comments = random.randint(3, 8)
        self.logger.debug("Vendo ~%d comentarios...", num_comments)

        for _ in range(num_comments):
            if self._should_stop(stop_check):
                break

            px = random.randint(250, 500)
            drv.execute_script(f"window.scrollBy(0, {px});")

            # Snap to the nearest reply tweet.
            self._snap_to_nearest_tweet(drv)

            # "Read" the comment.
            read_time = random.uniform(2.0, 6.0)
            time.sleep(read_time)

        # Small pause before going back.
        random_delay(1.0, 3.0)

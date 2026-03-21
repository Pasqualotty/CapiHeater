"""
Human-like timing and behavior utilities.
Provides Gaussian delays, random scrolling, and jittered pauses
to mimic organic user interaction.
"""

import random
import time

from utils.config import (
    MEAN_ACTION_DELAY,
    MAX_ACTION_DELAY,
    MAX_PAGE_LOAD_WAIT,
    MAX_SCROLL_PAUSE,
    MIN_ACTION_DELAY,
    MIN_PAGE_LOAD_WAIT,
    MIN_SCROLL_PAUSE,
    STD_ACTION_DELAY,
)


def gaussian_delay(
    mean: float = MEAN_ACTION_DELAY,
    std: float = STD_ACTION_DELAY,
    minimum: float = MIN_ACTION_DELAY,
    maximum: float = MAX_ACTION_DELAY,
) -> float:
    """
    Sleep for a duration drawn from a Gaussian distribution,
    clamped between minimum and maximum.
    Returns the actual delay used.
    """
    delay = max(minimum, min(maximum, random.gauss(mean, std)))
    time.sleep(delay)
    return delay


def random_delay(low: float = MIN_ACTION_DELAY, high: float = MAX_ACTION_DELAY) -> float:
    """Sleep for a uniformly random duration between low and high."""
    delay = random.uniform(low, high)
    time.sleep(delay)
    return delay


def page_load_wait() -> float:
    """Wait a human-like duration after navigating to a new page."""
    return random_delay(MIN_PAGE_LOAD_WAIT, MAX_PAGE_LOAD_WAIT)


def scroll_pause() -> float:
    """Short pause between scroll actions."""
    return random_delay(MIN_SCROLL_PAUSE, MAX_SCROLL_PAUSE)


def human_scroll(driver, scrolls: int = None):
    """
    Perform a series of random scroll actions on the page.

    Args:
        driver: Selenium WebDriver instance.
        scrolls: Number of scroll actions. If None, a random count (2-5) is chosen.
    """
    if scrolls is None:
        scrolls = random.randint(2, 5)

    for _ in range(scrolls):
        direction = random.choice(["down", "down", "down", "up"])  # bias downward
        distance = random.randint(200, 700)

        if direction == "up":
            distance = -distance

        driver.execute_script(f"window.scrollBy(0, {distance})")
        scroll_pause()


def human_typing_delay(text: str) -> float:
    """
    Return a total delay proportional to the length of text,
    simulating human typing speed (~100-250 ms per character).
    Does NOT sleep; the caller should use this for per-character delays.
    """
    per_char = random.uniform(0.10, 0.25)
    return len(text) * per_char


def type_like_human(element, text: str):
    """
    Type text into a Selenium element one character at a time
    with randomized per-keystroke delays.

    Args:
        element: Selenium WebElement with send_keys support.
        text: The string to type.
    """
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.22))


def jitter(base: float, factor: float = 0.3) -> float:
    """
    Return base +/- (factor * base) as a random jitter.
    Useful for adding variance to fixed delays.
    """
    offset = base * factor
    return random.uniform(base - offset, base + offset)


def should_skip_action(skip_probability: float = 0.1) -> bool:
    """Randomly decide whether to skip an action, adding unpredictability."""
    return random.random() < skip_probability

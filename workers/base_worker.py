"""
BaseWorker - Abstract threaded worker with stop/pause support.
"""

import threading
from abc import ABC, abstractmethod


class BaseWorker(threading.Thread, ABC):
    """Base class for all CapiHeater worker threads.

    Provides cooperative stop and pause semantics via ``threading.Event``
    objects that subclasses should check between atomic units of work.
    """

    def __init__(self, name: str = "Worker", **kwargs):
        super().__init__(name=name, daemon=True, **kwargs)
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        # Start in "not paused" state (event is *set* when NOT paused)
        self._pause_event.set()

    # ------------------------------------------------------------------
    # Control methods
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Signal the worker to stop at the next safe point."""
        self._stop_event.set()
        # Also un-pause so the thread can actually reach the stop check
        self._pause_event.set()

    def pause(self) -> None:
        """Signal the worker to pause at the next safe point."""
        self._pause_event.clear()

    def resume(self) -> None:
        """Resume a paused worker."""
        self._pause_event.set()

    def is_stopped(self) -> bool:
        """Return True if a stop has been requested."""
        return self._stop_event.is_set()

    def is_paused(self) -> bool:
        """Return True if the worker is currently paused."""
        return not self._pause_event.is_set()

    # ------------------------------------------------------------------
    # Helpers for subclasses
    # ------------------------------------------------------------------

    def wait_if_paused(self) -> bool:
        """Block until un-paused.  Returns False if stop was requested
        while waiting, True otherwise.

        Subclasses should call this between actions::

            if not self.wait_if_paused():
                return  # stop requested
        """
        self._pause_event.wait()
        return not self.is_stopped()

    def should_continue(self) -> bool:
        """Quick check: not stopped and not paused (or waits if paused).

        Returns True if the worker should keep going.
        """
        if self.is_stopped():
            return False
        return self.wait_if_paused()

    # ------------------------------------------------------------------
    # Abstract
    # ------------------------------------------------------------------

    @abstractmethod
    def run(self) -> None:
        """Main worker loop — must be implemented by subclasses."""
        ...

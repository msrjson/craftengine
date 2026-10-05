"""Per-extension circuit breaker: a failing extension stops being called.

Closed: calls go through, unexpected failures are counted inside a sliding
window. Open: once the count reaches the threshold, calls are refused without
running the extension, for `cooldown` seconds. Half-open: after the cooldown a
single trial call goes through; success closes the breaker, failure opens it
again for another cooldown.

The breaker lives in the worker process: each worker learns about a failing
extension from its own failures, which keeps it free of shared state.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum


class BreakerState(StrEnum):
    """Where an extension's breaker stands."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class _Circuit:
    """Failure history and state of one extension."""

    failures: deque[float] = field(default_factory=deque)
    opened_at: float | None = None
    trial_in_flight: bool = False
    last_error: str = ""


class CircuitBreaker:
    """Track failures per extension slug and decide whether it may run.

    Args:
        threshold: Unexpected failures inside `window` that open the breaker.
        window: Seconds the failures are counted over.
        cooldown: Seconds an open breaker refuses calls before a trial.
        clock: Monotonic time source, injectable for tests.
    """

    def __init__(
        self,
        threshold: int = 5,
        window: float = 60.0,
        cooldown: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.threshold = max(1, int(threshold))
        self.window = float(window)
        self.cooldown = float(cooldown)
        self._clock = clock
        self._circuits: dict[str, _Circuit] = {}
        self._lock = threading.Lock()

    def allow(self, slug: str) -> bool:
        """Return whether a call into `slug` may run now.

        An open breaker past its cooldown lets exactly one trial call through.
        """
        with self._lock:
            circuit = self._circuits.get(slug)
            if circuit is None or circuit.opened_at is None:
                return True
            if self._clock() - circuit.opened_at < self.cooldown or circuit.trial_in_flight:
                return False
            circuit.trial_in_flight = True
            return True

    def state(self, slug: str) -> BreakerState:
        """Return the breaker state of `slug`, without consuming a trial."""
        with self._lock:
            circuit = self._circuits.get(slug)
            if circuit is None or circuit.opened_at is None:
                return BreakerState.CLOSED
            elapsed = self._clock() - circuit.opened_at
            return BreakerState.OPEN if elapsed < self.cooldown else BreakerState.HALF_OPEN

    def record_success(self, slug: str) -> None:
        """Close the breaker of `slug` after a successful trial call."""
        with self._lock:
            circuit = self._circuits.get(slug)
            if circuit is not None and circuit.opened_at is not None and circuit.trial_in_flight:
                self._circuits[slug] = _Circuit()

    def record_failure(self, slug: str, error: str = "") -> bool:
        """Count one unexpected failure of `slug`; return True when it opens the breaker."""
        with self._lock:
            circuit = self._circuits.setdefault(slug, _Circuit())
            now = self._clock()
            circuit.last_error = error
            if circuit.opened_at is not None:
                circuit.opened_at, circuit.trial_in_flight = now, False
                return False
            circuit.failures.append(now)
            while circuit.failures and now - circuit.failures[0] > self.window:
                circuit.failures.popleft()
            if len(circuit.failures) < self.threshold:
                return False
            circuit.opened_at = now
            circuit.failures.clear()
            return True

    def last_error(self, slug: str) -> str:
        """Return the code of the last failure recorded for `slug`."""
        with self._lock:
            circuit = self._circuits.get(slug)
            return circuit.last_error if circuit else ""

    def reset(self, slug: str) -> None:
        """Forget every failure of `slug`, e.g. after it is re-activated."""
        with self._lock:
            self._circuits.pop(slug, None)


__all__ = ["BreakerState", "CircuitBreaker"]

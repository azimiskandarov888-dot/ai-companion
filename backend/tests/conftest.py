"""Shared for every test."""

import pytest


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """Each test starts with no requests counted against any door (guard.py): the limiter is per process, and the
    suite opens many sockets and calls from one address."""
    from app import guard
    guard.LIMITER.clear()
    yield
    guard.LIMITER.clear()

"""Tests for LogBroadcaster / JobLog WebSocket streamer."""
from __future__ import annotations

import asyncio

import pytest

from installer.web.ws import JobLog, LogBroadcaster


class TestJobLog:
    def test_append_delivers_to_subscriber(self):
        log = JobLog(job_id="j1")
        q = log.subscribe()
        log.append("hello")
        assert q.get_nowait() == "hello"

    def test_subscribe_replays_existing_lines(self):
        log = JobLog(job_id="j2")
        log.append("line1")
        log.append("line2")
        q = log.subscribe()
        assert q.get_nowait() == "line1"
        assert q.get_nowait() == "line2"

    def test_finish_sends_sentinel(self):
        log = JobLog(job_id="j3")
        q = log.subscribe()
        log.finish()
        assert q.get_nowait() is None

    def test_finish_on_already_done_log_replays_sentinel_on_subscribe(self):
        log = JobLog(job_id="j4")
        log.finish()
        q = log.subscribe()
        assert q.get_nowait() is None

    def test_unsubscribe_stops_delivery(self):
        log = JobLog(job_id="j5")
        q = log.subscribe()
        log.unsubscribe(q)
        log.append("missed")
        assert q.empty()

    def test_unsubscribe_missing_queue_is_safe(self):
        log = JobLog(job_id="j6")
        import asyncio
        stray: asyncio.Queue = asyncio.Queue()
        log.unsubscribe(stray)  # must not raise

    def test_multiple_subscribers(self):
        log = JobLog(job_id="j7")
        q1, q2 = log.subscribe(), log.subscribe()
        log.append("broadcast")
        assert q1.get_nowait() == "broadcast"
        assert q2.get_nowait() == "broadcast"


class TestLogBroadcaster:
    def test_create_and_get(self):
        bc = LogBroadcaster()
        log = bc.create("abc")
        assert bc.get("abc") is log

    def test_get_missing_returns_none(self):
        bc = LogBroadcaster()
        assert bc.get("nope") is None

    def test_remove(self):
        bc = LogBroadcaster()
        bc.create("xyz")
        bc.remove("xyz")
        assert bc.get("xyz") is None

    def test_remove_missing_is_safe(self):
        bc = LogBroadcaster()
        bc.remove("ghost")  # must not raise

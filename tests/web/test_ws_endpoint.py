"""Integration tests for the /ws/logs/{job_id} WebSocket endpoint."""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from installer.web.server import app
from installer.web.ws import broadcaster


@pytest.fixture(autouse=True)
def clean_broadcaster():
    """Remove any jobs created during a test."""
    yield
    # clear all jobs after each test
    broadcaster._jobs.clear()


client = TestClient(app)

from starlette.websockets import WebSocketDisconnect as _WSDisconnect


# ── Helpers ────────────────────────────────────────────────────────────────────

def ws_collect(job_id: str, max_msgs: int = 20) -> list[str]:
    """Connect and collect messages; tolerates server-side close after [done]."""
    messages: list[str] = []
    try:
        with client.websocket_connect(f"/ws/logs/{job_id}") as ws:
            for _ in range(max_msgs):
                try:
                    msg = ws.receive_text()
                except _WSDisconnect:
                    break
                messages.append(msg)
                if msg == "[done]" or msg.startswith("[error]"):
                    break
    except _WSDisconnect:
        pass
    return messages


# ── Tests: missing job ─────────────────────────────────────────────────────────

def test_ws_unknown_job_sends_error_and_closes():
    msgs = ws_collect("no-such-job")
    assert any(m.startswith("[error]") for m in msgs)
    assert any("no-such-job" in m for m in msgs)


# ── Tests: immediate finish ────────────────────────────────────────────────────

def test_ws_already_finished_job_sends_lines_then_done():
    job = broadcaster.create("j-finished")
    job.append("line-a")
    job.append("line-b")
    job.finish()

    msgs = ws_collect("j-finished")
    assert "line-a" in msgs
    assert "line-b" in msgs
    assert msgs[-1] == "[done]"


def test_ws_empty_finished_job_sends_done():
    job = broadcaster.create("j-empty")
    job.finish()

    msgs = ws_collect("j-empty")
    assert msgs == ["[done]"]


# ── Tests: live streaming ──────────────────────────────────────────────────────

def test_ws_streams_lines_appended_after_connect():
    job = broadcaster.create("j-live")

    received: list[str] = []

    def producer():
        job.append("hello")
        job.append("world")
        job.finish()

    with client.websocket_connect("/ws/logs/j-live") as ws:
        producer()
        for _ in range(5):
            msg = ws.receive_text()
            received.append(msg)
            if msg == "[done]":
                break

    assert "hello" in received
    assert "world" in received
    assert received[-1] == "[done]"


def test_ws_multiple_lines_delivered_in_order():
    job = broadcaster.create("j-order")
    lines = [f"line-{i}" for i in range(10)]
    for ln in lines:
        job.append(ln)
    job.finish()

    msgs = ws_collect("j-order")
    text_msgs = [m for m in msgs if m != "[done]"]
    assert text_msgs == lines


# ── Tests: multiple simultaneous subscribers ───────────────────────────────────

def test_ws_two_clients_both_receive_all_lines():
    job = broadcaster.create("j-multi")
    job.append("shared-1")
    job.append("shared-2")
    job.finish()

    msgs_a = ws_collect("j-multi")
    msgs_b = ws_collect("j-multi")

    for msgs in (msgs_a, msgs_b):
        assert "shared-1" in msgs
        assert "shared-2" in msgs
        assert "[done]" in msgs


# ── Tests: broadcaster lifecycle ───────────────────────────────────────────────

def test_broadcaster_remove_makes_job_unavailable():
    broadcaster.create("j-rm")
    broadcaster.remove("j-rm")

    msgs = ws_collect("j-rm")
    assert any(m.startswith("[error]") for m in msgs)


def test_broadcaster_create_returns_new_job_each_time():
    j1 = broadcaster.create("j-new1")
    j2 = broadcaster.create("j-new2")
    assert j1 is not j2
    assert j1.job_id == "j-new1"
    assert j2.job_id == "j-new2"


# ── Tests: job log replay correctness ─────────────────────────────────────────

def test_late_subscriber_gets_all_previous_lines():
    job = broadcaster.create("j-replay")
    for i in range(5):
        job.append(f"early-{i}")

    # subscribe after lines are already written
    q = job.subscribe()
    for i in range(5):
        assert q.get_nowait() == f"early-{i}"


def test_late_subscriber_on_done_job_gets_sentinel():
    job = broadcaster.create("j-replay-done")
    job.append("x")
    job.finish()

    q = job.subscribe()
    assert q.get_nowait() == "x"
    assert q.get_nowait() is None   # sentinel


# ── Tests: ping (timeout path) — unit level ────────────────────────────────────

def test_job_log_append_after_unsubscribe_does_not_raise():
    job = broadcaster.create("j-unsub")
    q = job.subscribe()
    job.unsubscribe(q)
    job.append("ghost")          # must not raise
    assert q.empty()


def test_job_log_finish_after_unsubscribe_does_not_raise():
    job = broadcaster.create("j-unsub-finish")
    q = job.subscribe()
    job.unsubscribe(q)
    job.finish()                 # must not raise

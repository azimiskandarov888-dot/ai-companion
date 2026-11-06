"""The doors a stranger with a script must find shut (guard.py; the frontend audit, 2026-11-07)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import allowance, brain, config, guard, identity, main, stt, tts

TOKEN = "aVerYlOngRandomLookingTokenFromTheKeychain_guard_0123456789"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
UID = identity.user_id_from_token(TOKEN)


@pytest.fixture
def client(monkeypatch):
    async def fake_reply(history, system_stable, system_variable="", *, fresh_info=False):
        return "Тёплый ответ."

    async def fake_tts(text, voice=None, *, rate=1.0):
        return b"FAKEMP3"

    async def fake_stt(audio_bytes, filename="audio.webm"):
        return "привет"

    monkeypatch.setattr(brain, "generate_reply", fake_reply)
    monkeypatch.setattr(tts, "synthesize", fake_tts)
    monkeypatch.setattr(tts, "configured", lambda: True)
    monkeypatch.setattr(stt, "transcribe", fake_stt)
    guard.LIMITER.clear()
    with TestClient(main.app) as c:
        yield c
    guard.LIMITER.clear()


# ── a public server: no token, no entry; no developer pages; no word-for-word voice

@pytest.mark.parametrize("method,path", [("get", "/api/diary"), ("get", "/api/memory"), ("get", "/api/alerts"),
                                         ("delete", "/api/me"), ("get", "/api/usage")])
def test_public_server_refuses_requests_without_a_token(client, monkeypatch, method, path):
    monkeypatch.setattr(config, "PUBLIC", True)
    assert getattr(client, method)(path).status_code == 401


def test_public_server_hides_the_developer_pages(client, monkeypatch):
    monkeypatch.setattr(config, "PUBLIC", True)
    assert client.get("/").status_code == 404
    assert client.get("/live").status_code == 404


def test_public_server_will_not_speak_anything_word_for_word(client, monkeypatch):
    monkeypatch.setattr(config, "PUBLIC", True)
    r = client.post("/api/say", json={"text": "anything at all", "verbatim": True}, headers=AUTH)
    assert r.status_code == 403


def test_at_home_the_anonymous_bucket_still_works(client):
    # (BOB_PUBLIC off: the browser dev page and curl keep working, as before)
    assert client.get("/api/health").status_code == 200


# ── uploads and texts have a size

def test_talk_refuses_an_upload_past_the_cap(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_AUDIO_BYTES", 1000)
    r = client.post("/api/talk", files={"audio": ("a.m4a", b"x"*1001, "audio/mp4")}, headers=AUTH)
    assert r.status_code == 413


def test_say_refuses_a_text_past_its_length(client):
    r = client.post("/api/say", json={"text": "a"*2001}, headers=AUTH)
    assert r.status_code == 422


# ── /api/say is a paid call: it counts against the day, and a spent day stops it

def test_say_stops_when_the_day_is_spent(client, monkeypatch):
    called = []

    async def counting_reply(*a, **k):
        called.append(1)
        return "не должно прозвучать"

    monkeypatch.setattr(brain, "generate_reply", counting_reply)
    monkeypatch.setattr(allowance, "check", lambda uid: allowance.Verdict(False, "На сегодня всё.", "daily_limit", 0))
    r = client.post("/api/say", json={"text": "ещё поговорим?"}, headers=AUTH)
    assert r.status_code == 200 and r.json()["state"] == "daily_limit"
    assert called == []


# ── the dear doors are limited per address

def test_making_companions_is_rate_limited(client, monkeypatch):
    monkeypatch.setitem(guard.LIMITS, "create", (2, 3600))
    codes = [client.post("/api/companion/create", json={"about": "", "wishes": ""}, headers=AUTH).status_code for _ in range(3)]
    assert codes[-1] == 429


def test_his_hello_is_rate_limited(client, monkeypatch):
    monkeypatch.setitem(guard.LIMITS, "hello", (1, 3600))
    client.post("/api/hello", headers=AUTH)
    assert client.post("/api/hello", headers=AUTH).status_code == 429


def test_limiter_counts_a_window():
    lim = guard.Limiter()
    assert all(lim.allow("k", 3, 60) for _ in range(3))
    assert not lim.allow("k", 3, 60)
    assert lim.allow("other", 3, 60)


def test_forwarded_address_is_trusted_only_behind_a_proxy(monkeypatch):
    monkeypatch.setattr(config, "TRUST_PROXY", False)
    assert guard.address("10.0.0.1", "1.2.3.4") == "10.0.0.1"
    monkeypatch.setattr(config, "TRUST_PROXY", True)
    assert guard.address("10.0.0.1", "1.2.3.4, 10.0.0.1") == "1.2.3.4"

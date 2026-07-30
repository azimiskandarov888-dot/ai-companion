"""Endpoint tests — the voice loop wired end to end, with services mocked.

The AI services (Claude, Whisper, ElevenLabs) are replaced with fast fakes so we
test the orchestration (persona + memory + logging), not the network.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import brain, learn, main, memory, stt, tts


@pytest.fixture
def client(monkeypatch):
    async def fake_reply(history, system_prompt):
        return "Тёплый ответ от Боба."

    async def fake_tts(text):
        return b"FAKEMP3"

    async def fake_stt(audio_bytes, filename="audio.webm"):
        return "привет, Боб"

    async def fake_learn(*args, **kwargs):
        return None

    monkeypatch.setattr(brain, "generate_reply", fake_reply)
    monkeypatch.setattr(tts, "synthesize", fake_tts)
    monkeypatch.setattr(tts, "configured", lambda: True)  # simulate a real voice
    monkeypatch.setattr(stt, "transcribe", fake_stt)
    monkeypatch.setattr(learn, "learn_from_exchange", fake_learn)

    with TestClient(main.app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["companion_name"]
    assert set(data["services"]) == {"brain_claude", "ears_whisper", "mouth"}


def test_index_served(client):
    assert client.get("/").status_code == 200


def test_say_happy_path(client):
    r = client.post("/api/say", json={"text": "доброе утро", "session_id": "t"})
    assert r.status_code == 200
    data = r.json()
    assert data["reply"] == "Тёплый ответ от Боба."
    assert data["audio_base64"]  # base64 of FAKEMP3
    turns = memory.recent_turns("t")
    assert turns[-1]["role"] == "assistant"
    assert any(t["content"] == "доброе утро" for t in turns)


def test_say_empty_is_400(client):
    assert client.post("/api/say", json={"text": "   "}).status_code == 400


def test_say_without_voice_falls_back_to_client(client, monkeypatch):
    # MVP path: no ElevenLabs configured → no server audio, and the client is
    # told to speak the reply itself (the browser's free voice).
    monkeypatch.setattr(tts, "configured", lambda: False)
    data = client.post("/api/say", json={"text": "привет", "session_id": "t4"}).json()
    assert data["reply"] == "Тёплый ответ от Боба."
    assert data["audio_base64"] == ""
    assert data["voice"] == "client"


def test_talk_happy_path(client):
    r = client.post(
        "/api/talk",
        files={"audio": ("a.webm", b"somebytes", "audio/webm")},
        data={"session_id": "t2"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["transcript"] == "привет, Боб"
    assert data["reply"] == "Тёплый ответ от Боба."


def test_talk_empty_audio_is_400(client):
    r = client.post("/api/talk", files={"audio": ("a.webm", b"", "audio/webm")})
    assert r.status_code == 400


def test_memory_endpoint_shape(client):
    client.post("/api/say", json={"text": "привет", "session_id": "t3"})
    data = client.get("/api/memory").json()
    assert "elder" in data and "bob" in data and "memories" in data

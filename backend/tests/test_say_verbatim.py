"""Verbatim mode — the background-voice test's only backend dependency.

Two things must be true, and the second is the one that would quietly cause
damage if it broke: the line must come back spoken exactly as sent, and it must
NOT be remembered. A test phrase logged as a real memory would end up in his
diary as something his friend said.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import main, tts


def test_verbatim_speaks_the_line_exactly(monkeypatch):
    monkeypatch.setattr(tts, "configured", lambda: True)

    spoken: list[str] = []

    async def fake_synthesize(text: str, voice=None) -> bytes:
        spoken.append(text)
        return b"fake-mp3-bytes"

    monkeypatch.setattr(tts, "synthesize", fake_synthesize)

    with TestClient(main.app) as client:
        response = client.post(
            "/api/say",
            json={"text": "Я здесь. Слышишь меня?", "verbatim": True},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Я здесь. Слышишь меня?"
    assert body["voice"] == "server"
    assert body["audio_base64"]
    # The line reached the voice untouched — not rephrased, not answered.
    assert spoken == ["Я здесь. Слышишь меня?"]


def test_verbatim_does_not_become_a_memory(monkeypatch):
    """The test phrase must never turn up in his diary."""
    monkeypatch.setattr(tts, "configured", lambda: True)

    async def fake_synthesize(text: str, voice=None) -> bytes:
        return b"fake-mp3-bytes"

    monkeypatch.setattr(tts, "synthesize", fake_synthesize)

    logged: list[tuple] = []
    monkeypatch.setattr(
        main.memory, "log_turn", lambda *a, **k: logged.append(a)
    )

    learned: list[tuple] = []

    async def fake_learn(*args, **kwargs):
        learned.append(args)

    monkeypatch.setattr(main.learn, "learn_from_exchange", fake_learn)

    with TestClient(main.app) as client:
        client.post(
            "/api/say",
            json={"text": "Проверка связи", "verbatim": True},
        )

    assert logged == [], "a verbatim line was written to the conversation log"
    assert learned == [], "a verbatim line was sent to be learned as a memory"


def test_verbatim_without_a_voice_configured_still_answers(monkeypatch):
    """No voice key: the app is told to speak it itself rather than failing."""
    monkeypatch.setattr(tts, "configured", lambda: False)

    with TestClient(main.app) as client:
        response = client.post(
            "/api/say", json={"text": "Я здесь.", "verbatim": True}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Я здесь."
    assert body["voice"] == "client"
    assert body["audio_base64"] == ""

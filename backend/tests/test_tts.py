"""The voice (TTS): provider selection (Fish Audio default, ElevenLabs, or none)."""

from __future__ import annotations

from app import config, tts


def test_fish_is_configured_when_key_present(monkeypatch):
    monkeypatch.setattr(config, "TTS_PROVIDER", "fish")
    monkeypatch.setattr(config, "FISH_API_KEY", "fish-key")
    assert tts.configured() is True
    assert tts.provider_name() == "fish"

    monkeypatch.setattr(config, "FISH_API_KEY", None)
    assert tts.configured() is False  # no key → client speaks free


def test_elevenlabs_needs_key_and_voice(monkeypatch):
    monkeypatch.setattr(config, "TTS_PROVIDER", "elevenlabs")
    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "el-key")
    monkeypatch.setattr(config, "ELEVENLABS_VOICE_ID", "voice")
    assert tts.configured() is True

    monkeypatch.setattr(config, "ELEVENLABS_VOICE_ID", "")
    assert tts.configured() is False


def test_no_provider_means_client_voice(monkeypatch):
    monkeypatch.setattr(config, "TTS_PROVIDER", "")
    assert tts.configured() is False
    assert tts.provider_name() == "none"

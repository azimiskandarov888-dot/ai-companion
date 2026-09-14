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


# ── the voice actually slows down ───────────────────────────────────────────
#
# The register has counted «просил помедленнее» and «не расслышал» for months,
# and the only thing that ever happened was a line in the prompt asking for
# shorter sentences. That helps, and it is not what was asked for. The knob is
# on the API — and a rule that can be replaced by a mechanism should be.

def test_an_ordinary_person_is_spoken_to_at_the_ordinary_rate(tmp_path, monkeypatch):
    from app import config, db

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    db.init_db()
    assert tts.rate_for("u") == 1.0
    assert tts.rate_for(None) == 1.0


def test_somebody_who_keeps_asking_again_is_spoken_to_slower(tmp_path, monkeypatch):
    """Both signals count toward the same conclusion, and neither waits for two
    on its own: people with poor hearing do not complain, they get used to it."""
    from app import config, db, mood

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    db.init_db()
    mood.observe("u", "просил_помедленнее", "")
    assert tts.rate_for("u") == 1.0                 # once is a coincidence
    mood.observe("u", "не_расслышал", "")
    assert tts.rate_for("u") == tts.SLOWER


def test_it_is_easier_to_follow_and_not_a_voice_talking_to_a_child():
    """The insult this app can least afford to give. 0.85 is noticeably easier
    to catch; theatrical slowness is its own kind of contempt."""
    assert 0.8 <= tts.SLOWER < 0.95


def test_the_rate_never_takes_the_voice_down(tmp_path, monkeypatch):
    """A friend speaking at the wrong speed is a small problem. A friend who
    has gone silent is the whole product failing."""
    from app import config

    monkeypatch.setattr(config, "DB_PATH", "/nonexistent/nowhere.db")
    assert tts.rate_for("u") == 1.0


def test_a_broken_speed_setting_does_not_silence_him_either():
    assert tts._base_speed("") == 1.0
    assert tts._base_speed("не число") == 1.0
    assert tts._base_speed("0.95") == 0.95

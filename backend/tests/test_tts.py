"""The voice (TTS): provider selection (Fish Audio default, ElevenLabs, or none),
and his sounds — played by a voice that can make them, removed by one that can't."""

from __future__ import annotations

import asyncio
import json

import httpx

from app import body, config, tts


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


# --------------------------------------------------------------------------- #
# His sounds
# --------------------------------------------------------------------------- #
def _fish_s2(monkeypatch, provider: str = "openrouter") -> None:
    monkeypatch.setattr(config, "TTS_PROVIDER", provider)
    monkeypatch.setattr(config, "FISH_MODEL", "s2.1-pro")
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(config, "FISH_API_KEY", "test-key")


def test_a_cough_is_played_not_read():
    said = tts.spoken(f"Горло уже {body.MARK_COUGH} извини. Так вот.", sounds=True)
    assert said == "Горло уже [cough] извини. Так вот."


def test_every_sound_is_one_of_his_markers_and_a_tag_in_brackets():
    """Brackets, never parentheses: «(clears throat)» came out as «Силле…
    строт», and «(yawning)» was spelled out letter by letter."""
    for mark, tag in tts.SOUNDS.items():
        assert mark in body.MARKERS
        assert tag.startswith("[") and tag.endswith("]")
        assert tts.spoken(f"Ну. {mark} Да.", sounds=True) == f"Ну. {tag} Да."


def test_a_sound_the_voice_cannot_make_is_removed_not_read():
    """A sneeze came out as a sniff — so it is not in the table, and a marker
    that is not in the table is taken out, exactly as before."""
    assert body.MARK_SNEEZE not in tts.SOUNDS
    assert tts.spoken(f"{body.MARK_SNEEZE} Ой, извини.", sounds=True) == "Ой, извини."


def test_brackets_he_writes_himself_never_reach_the_voice_as_a_tag():
    """The voice acts on whatever is in square brackets. Only OUR tags may get
    there; a «[whispers]» of the model's own is removed as it always was."""
    assert tts.spoken("[whispers] Слушай. [laughs] Да.", sounds=True) == "Слушай. Да."


def test_a_sound_inside_a_stage_direction_goes_with_it():
    said = tts.spoken(f"Да. *{body.MARK_SIGH} смотрит в окно* Ну вот.", sounds=True)
    assert said == "Да. Ну вот."
    assert "\x00" not in said


def test_without_sounds_every_marker_is_removed():
    for mark in body.MARKERS:
        assert tts.spoken(f"Ну. {mark} Да.") == "Ну. Да."


def test_only_fish_s2_speaking_from_the_server_makes_them(monkeypatch):
    _fish_s2(monkeypatch)
    assert tts.makes_sounds()
    assert tts.makes(body.MARK_COUGH) and tts.makes(body.MARK_LAUGH)
    assert not tts.makes(body.MARK_SNEEZE)
    monkeypatch.setattr(config, "TTS_PROVIDER", "fish")
    assert tts.makes_sounds()
    # The old model plays nothing.
    monkeypatch.setattr(config, "FISH_MODEL", "s1")
    assert not tts.makes_sounds()
    # «fish» with no Fish key but an OpenRouter one is the same voice through
    # OpenRouter — it still plays them (config.voice_provider).
    monkeypatch.setattr(config, "FISH_MODEL", "s2.1-pro")
    monkeypatch.setattr(config, "FISH_API_KEY", None)
    assert config.voice_provider() == "openrouter"
    assert tts.makes_sounds()
    # No server voice at all: the phone speaks, and it cannot.
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", None)
    assert not tts.makes_sounds()
    monkeypatch.setattr(config, "TTS_PROVIDER", "openai")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-key")
    assert not tts.makes_sounds()


def test_a_lone_cough_is_something_to_say_only_to_a_voice_that_makes_it(monkeypatch):
    _fish_s2(monkeypatch)
    assert tts.audible(body.MARK_COUGH)
    assert not tts.audible("*пауза*")
    monkeypatch.setattr(config, "FISH_MODEL", "s1")
    assert not tts.audible(body.MARK_COUGH)


def test_the_sound_reaches_the_voice_through_openrouter(monkeypatch):
    _fish_s2(monkeypatch)
    sent: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, content=b"MP3")

    real = httpx.AsyncClient
    monkeypatch.setattr(tts.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(answer), **kw))
    audio = asyncio.run(tts.synthesize(f"Горло {body.MARK_COUGH} извини.", "voice-id"))

    assert audio == b"MP3"
    [request] = sent
    assert str(request.url) == "https://openrouter.ai/api/v1/audio/speech"
    assert request.headers["authorization"] == "Bearer test-key"
    assert json.loads(request.content) == {
        "model": "fish-audio/s2.1-pro",
        "input": "Горло [cough] извини.",
        "response_format": "mp3",
        "voice": "voice-id",
    }


def test_a_woman_keeps_her_voice_through_openrouter(monkeypatch):
    monkeypatch.setattr(config, "TTS_PROVIDER", "openrouter")
    monkeypatch.setattr(config, "FISH_VOICE_ID_FEMALE", "her-voice")
    assert tts.voice_for({"gender": "женский"}) == "her-voice"


def test_openrouter_is_configured_by_its_key(monkeypatch):
    monkeypatch.setattr(config, "TTS_PROVIDER", "openrouter")
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    assert tts.configured()
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", None)
    assert not tts.configured()


# --------------------------------------------------------------------------- #
# His voice as it is made — the live channel (live.py)
# --------------------------------------------------------------------------- #
class _Chunks(httpx.AsyncByteStream):
    def __init__(self, parts: list[bytes]) -> None:
        self.parts = parts

    async def __aiter__(self):
        for part in self.parts:
            yield part


def test_his_voice_arrives_as_it_is_made_in_whole_samples(monkeypatch):
    """A byte split across two pieces is a click; the rate is the one the
    voice says it is sending."""
    _fish_s2(monkeypatch)
    sent: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, headers={"content-type": "audio/pcm;rate=22050;channels=1"},
                              stream=_Chunks([b"\x01", b"\x02\x03", b"\x04\x05\x06"]))

    client = httpx.AsyncClient(transport=httpx.MockTransport(answer))
    monkeypatch.setattr(tts, "_line", lambda: client)

    async def hear():
        return [piece async for piece in tts.stream(f"Горло {body.MARK_COUGH} извини.", "voice-id")]

    pieces = asyncio.run(hear())
    assert pieces == [(22050, b"\x01\x02"), (22050, b"\x03\x04\x05\x06")]
    assert json.loads(sent[0].content) == {
        "model": "fish-audio/s2.1-pro",
        "input": "Горло [cough] извини.",
        "response_format": "pcm",
        "voice": "voice-id",
    }


def test_a_voice_that_cannot_stream_is_said_plainly(monkeypatch):
    monkeypatch.setattr(config, "TTS_PROVIDER", "openai")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-key")

    async def hear():
        return [piece async for piece in tts.stream("Привет.")]

    import pytest

    with pytest.raises(RuntimeError, match="streams"):
        asyncio.run(hear())


def test_one_line_to_the_voice_stays_open(monkeypatch):
    """A fresh connection is 0.4 s of handshakes from Tashkent before a byte is
    asked for — and the old code paid it for every sentence."""
    monkeypatch.setattr(tts, "_client", None)
    monkeypatch.setattr(tts, "_client_loop", None)

    async def twice():
        return tts._line(), tts._line()

    first, second = asyncio.run(twice())
    assert first is second

    async def once():
        return tts._line()

    # …and made again only once the loop it belonged to is gone.
    assert asyncio.run(once()) is not first

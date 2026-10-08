"""The voice (TTS): provider selection (Gemini by default since 2026-10-03, Fish,
ElevenLabs, or none), and his sounds — played by a voice that can make them,
removed by one that can't."""

from __future__ import annotations

import asyncio
import time
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


def test_a_cough_is_played_not_read(monkeypatch):
    monkeypatch.setattr(config, "TTS_PROVIDER", "fish")
    said = tts.spoken(f"Горло уже {body.MARK_COUGH} извини. Так вот.", sounds=True)
    assert said == "Горло уже [cough] извини. Так вот."


def test_the_gemini_voices_get_their_own_tags_and_only_those(monkeypatch):
    """Google's tags, in angle brackets — and a marker Gemini has no tag for
    (a yawn, clearing the throat) is removed, never read out."""
    monkeypatch.setattr(config, "TTS_PROVIDER", "gemini")
    assert tts.spoken(f"Горло уже {body.MARK_COUGH} извини.", sounds=True) == "Горло уже <cough> извини."
    for mark, tag in tts.GEMINI_SOUNDS.items():
        assert mark in body.MARKERS and tag.startswith("<") and tag.endswith(">")
        assert tts.spoken(f"Ну. {mark} Да.", sounds=True) == f"Ну. {tag} Да."
    for mark in (body.MARK_YAWN, body.MARK_CLEAR, body.MARK_SNEEZE):
        assert tts.spoken(f"Ну. {mark} Да.", sounds=True) == "Ну. Да."
    # Angle brackets he writes himself never reach the voice as a tag.
    assert tts.spoken("Ну <laugh> да.", sounds=True) == "Ну laugh да."
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    assert tts.makes_sounds() and tts.makes(body.MARK_LAUGH) and not tts.makes(body.MARK_YAWN)


def test_every_sound_is_one_of_his_markers_and_a_tag_in_brackets(monkeypatch):
    """Brackets, never parentheses: «(clears throat)» came out as «Силле…
    строт», and «(yawning)» was spelled out letter by letter."""
    monkeypatch.setattr(config, "TTS_PROVIDER", "fish")
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

    with pytest.raises(RuntimeError, match="stream"):
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


# --------------------------------------------------------------------------- #
# The Gemini voices (the default since 2026-10-03)
# --------------------------------------------------------------------------- #
def test_a_gemini_voice_is_asked_for_by_name_with_whom_it_plays(monkeypatch):
    """voices.py: a voice from the catalog and a line about him — sent as
    Google's speech_metadata.style, never read out."""
    from app import voices

    monkeypatch.setattr(config, "TTS_PROVIDER", "gemini")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "google-key")
    key = voices.key({"name": "Zubenelgenubi", "style": "a man of 68, " + voices.MANNER})
    url, headers, payload = tts._gemini_direct_request("Ого, сам пишешь?", key)
    [part] = payload["contents"][0]["parts"]
    assert payload["generationConfig"]["speech_config"] == {"voice_config": {"voice": "Zubenelgenubi"}}
    assert part["speech_metadata"]["style"].startswith("a man of 68")
    # Somebody who has trouble following him: the voice takes no speed, so it is told.
    _, _, slower = tts._gemini_direct_request("Ого.", key, rate=tts.SLOWER)
    assert "slower" in slower["contents"][0]["parts"][0]["speech_metadata"]["style"]
    # No voice of his own (the template): the owner's best of thirty.
    _, _, plain = tts._gemini_direct_request("Ого.", None)
    assert plain["generationConfig"]["speech_config"]["voice_config"]["voice"] == tts.GEMINI_DEFAULT


def test_the_gemini_voice_reaches_a_file_as_wav(monkeypatch):
    """The same stream, gathered and wrapped — the phone plays files — and the
    file is said to be what it is."""
    import io
    import wave

    _google_and_router(monkeypatch)
    made = asyncio.run(tts.synthesize("Привет."))
    with wave.open(io.BytesIO(made)) as w:
        assert w.getframerate() == 24000 and w.getnchannels() == 1
        assert w.readframes(10_000) == b"\x01\x00" * 4 + b"\x02\x00" * 4
    assert tts.mime() == "audio/wav"
    monkeypatch.setattr(config, "TTS_PROVIDER", "fish")
    assert tts.mime() == "audio/mpeg"


def test_the_gemini_voice_streams_or_is_not_there(monkeypatch):
    """The owner: «We are never going to use non-streaming voice». No Google
    key, no Gemini voice — and nothing whole stands in for it."""
    monkeypatch.setattr(config, "TTS_PROVIDER", "gemini")
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "router-key")
    monkeypatch.setattr(config, "GEMINI_API_KEY", None)
    assert not tts.configured()
    monkeypatch.setattr(config, "GEMINI_API_KEY", "google-key")
    assert tts.configured() and tts.streams()


def _google_and_router(monkeypatch, google_status: int | list[int] = 200):
    """Google's stream and OpenRouter, both answered here. `google_status`: one
    answer for every request, or one for each in turn."""
    import base64

    asked: list[str] = []
    statuses = list(google_status) if isinstance(google_status, list) else None

    def answer(request: httpx.Request) -> httpx.Response:
        asked.append(request.url.host)
        if request.url.host == "generativelanguage.googleapis.com":
            status = statuses.pop(0) if statuses else google_status if statuses is None else 200
            if status == 429:
                return httpx.Response(429, content=json.dumps({"error": {"code": 429, "details": [
                    {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "0.05s"}]}}).encode())
            if status != 200:
                return httpx.Response(status, content=b'{"error": "nope"}')
            def audio(raw: bytes) -> dict:
                return {"candidates": [{"content": {"parts": [{"inlineData": {
                    "mimeType": "audio/L16;codec=pcm;rate=24000", "data": base64.b64encode(raw).decode()}}]}}]}

            events = [audio(b"\x01\x00" * 4), {"candidates": [{"content": {"parts": [{"text": "x"}]}}]},
                      audio(b"\x02\x00" * 4), {"usageMetadata": {}}]
            body = "".join(f"data: {json.dumps(e)}\n\n" for e in events)
            return httpx.Response(200, content=body.encode(), headers={"content-type": "text/event-stream"})
        return httpx.Response(200, content=b"\x03\x00" * 4, headers={"content-type": "audio/pcm;rate=24000"})

    monkeypatch.setattr(config, "TTS_PROVIDER", "gemini")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "google-key")
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "router-key")
    monkeypatch.setattr(tts, "_client", httpx.AsyncClient(transport=httpx.MockTransport(answer)))
    monkeypatch.setattr(tts, "_client_loop", None)
    return asked


def test_on_google_s_own_key_the_voice_streams(monkeypatch):
    """streamGenerateContent: the first sound while the rest is made."""
    asked = _google_and_router(monkeypatch)
    assert tts.streams()

    async def hear():
        return [piece async for piece in tts.stream("Ого, сам пишешь?")]

    pieces = asyncio.run(hear())
    assert pieces == [(24000, b"\x01\x00" * 4), (24000, b"\x02\x00" * 4)]
    assert asked == ["generativelanguage.googleapis.com"]
    url, headers, payload = tts._gemini_direct_request("Ого.", None)
    assert headers["x-goog-api-key"] == "google-key"
    assert config.GEMINI_TTS_MODEL.split("/", 1)[-1] in url and url.endswith(":streamGenerateContent?alt=sse")
    assert payload["generationConfig"]["speech_config"] == {"voice_config": {"voice": tts.GEMINI_DEFAULT}}
    [part] = payload["contents"][0]["parts"]
    assert part["text"] == "Ого." and part["speech_metadata"]["style"]   # whom he plays, never read


def test_when_google_refuses_it_is_said_and_nothing_whole_stands_in(monkeypatch):
    """A refusal is the turn's trouble, told to the phone (live.py) — never a
    slower voice made whole somewhere else."""
    import pytest

    asked = _google_and_router(monkeypatch, google_status=403)

    async def hear():
        return [piece async for piece in tts.stream("Ого.")]

    with pytest.raises(RuntimeError, match="403"):
        asyncio.run(hear())
    assert asked == ["generativelanguage.googleapis.com"]


def test_refused_for_the_minute_it_waits_as_told_and_asks_once_more(monkeypatch):
    """Ten requests a minute on a paid key's first tier (2026-10-07): a
    refusal for the minute is a pause in his words, not the end of them."""
    import pytest

    asked = _google_and_router(monkeypatch, google_status=[429, 200])

    async def hear():
        return [piece async for piece in tts.stream("Ого.")]

    assert asyncio.run(hear()) == [(24000, b"\x01\x00" * 4), (24000, b"\x02\x00" * 4)]
    assert asked == ["generativelanguage.googleapis.com"] * 2
    asked = _google_and_router(monkeypatch, google_status=429)    # and again: then it is said
    with pytest.raises(RuntimeError, match="429"):
        asyncio.run(hear())


def test_the_minute_s_requests_are_kept_to_and_his_words_come_first():
    """No eleventh request in a minute; and work nobody waits on (his sounds
    made ahead) leaves BACKGROUND_SPARE of them for his words."""
    budget = tts._Budget(3, window=0.3)

    async def run():
        for _ in range(3):
            await budget.take()
        assert budget.left() == 0
        began = asyncio.get_running_loop().time()
        await budget.take()                                   # waits for the window
        assert asyncio.get_running_loop().time() - began >= 0.25
        fresh = tts._Budget(3, window=0.3)
        await fresh.take()                                    # 2 left
        waited = asyncio.get_running_loop().time()
        await fresh.take(spare=2)                             # only while more than 2 are left
        assert asyncio.get_running_loop().time() - waited >= 0.25

    asyncio.run(run())


def test_a_voice_rationed_by_the_minute_is_said_so(monkeypatch):
    monkeypatch.setattr(config, "TTS_PROVIDER", "gemini")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "google-key")
    monkeypatch.setattr(config, "GEMINI_TTS_RPM", 10)
    assert tts.limited() and tts.room() == 10
    monkeypatch.setattr(config, "GEMINI_TTS_RPM", 0)
    assert not tts.limited() and tts.room() > 100


def test_refused_for_the_day_it_says_so_at_once_and_waits_no_hours(monkeypatch):
    """100 requests a day on the first tier: Google says to come back in hours.
    A turn is not left hanging — it is the turn's trouble, at once, and so is
    every request after it until then."""
    import pytest

    asked = _google_and_router(monkeypatch, google_status=429)
    monkeypatch.setattr(tts, "_retry_after", lambda detail: 26958.0)

    async def hear():
        return [piece async for piece in tts.stream("Ого.")]

    began = time.monotonic()
    with pytest.raises(RuntimeError, match="429"):
        asyncio.run(hear())
    with pytest.raises(RuntimeError, match="for the day"):
        asyncio.run(hear())
    assert time.monotonic() - began < 2
    assert asked == ["generativelanguage.googleapis.com"]          # the second never went


def test_with_a_google_cloud_key_the_voice_goes_to_google_cloud_unrationed(monkeypatch):
    """10 a minute and 100 a day on the AI Studio key; on Google Cloud the same
    voice and the same request, without that ration (2026-10-08)."""
    monkeypatch.setattr(config, "TTS_PROVIDER", "gemini")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "studio-key")
    monkeypatch.setattr(config, "GOOGLE_CLOUD_API_KEY", "cloud-key")
    monkeypatch.setattr(config, "GOOGLE_CLOUD_PROJECT", "gen-lang-client-1")
    url, headers, payload = tts._gemini_direct_request("Ого.", None)
    assert url.startswith("https://aiplatform.googleapis.com/v1/projects/gen-lang-client-1/locations/global/")
    assert "gemini-3.8-flash-lite-tts:streamGenerateContent" in url
    assert headers["x-goog-api-key"] == "cloud-key"
    assert payload["generationConfig"]["speech_config"]["voice_config"]["voice"]
    assert not tts.limited() and config.tts_configured()

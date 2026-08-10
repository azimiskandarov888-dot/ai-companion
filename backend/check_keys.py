"""Quick check that your API keys work — without ever showing them.

Run it from the `backend` folder, with your virtual environment active:

    python check_keys.py

It reads your keys from .env, gently pings Claude and OpenAI, and tells you in
plain words whether each one works. It never prints the key itself.
"""

from __future__ import annotations

import asyncio

from app import config


def _classify(error: Exception) -> str:
    """Turn a provider error into a plain-language reason."""
    name = type(error).__name__.lower()
    msg = str(error).lower()
    if "authentication" in name or "permissiondenied" in name or "401" in msg or "invalid x-api-key" in msg:
        return "rejected"
    # The voice providers don't raise typed errors — they come back as an HTTP
    # status inside the message, so read that too. 402/403 is nearly always a
    # spent balance; 404 is a voice ID that no longer exists.
    if "402" in msg or "403" in msg:
        return "no_credit"
    if any(word in msg for word in ("credit", "billing", "quota", "insufficient", "balance")):
        return "no_credit"
    if "notfound" in name or "not_found" in msg or "404" in msg:
        return "not_found"
    return "unreachable"


def venv_report() -> None:
    """Are we even running in the project's own environment?

    Running these scripts from conda's `base` (or the system Python) is by far
    the most common reason a check fails with ModuleNotFoundError — the packages
    are installed in .venv and nowhere else. The error itself doesn't say that,
    so this does.
    """
    import sys
    from pathlib import Path

    venv = Path(__file__).resolve().parent / ".venv"
    running_in_venv = str(venv) in sys.prefix or sys.prefix != sys.base_prefix

    if not running_in_venv:
        print(
            "⚠️  Не тот Python.\n\n"
            "   Пакеты стоят в backend/.venv, а сейчас запущен другой Python\n"
            f"   ({sys.prefix}).\n\n"
            "   Сначала выполните:\n"
            "       source .venv/bin/activate\n\n"
            "   В начале строки появится (.venv) вместо (base).\n"
        )


def shape_report() -> None:
    """What .env actually contains — shapes only, never the keys themselves.

    Nearly every 401 is one of four boring things: the key isn't loaded at all,
    it has quotes or spaces around it, it was pasted truncated, or it's the
    wrong kind of key. All four show up here without anything secret being
    printed.
    """
    print("What .env is giving the app:\n")

    def describe(name: str, value: str | None, expect: str) -> None:
        if not value:
            print(f"  {name:<20} MISSING — not set at all")
            return
        problems = []
        if value != value.strip():
            problems.append("has spaces around it")
        if value[:1] in "\"'" or value[-1:] in "\"'":
            problems.append("has quotes around it — remove them")
        if not value.startswith(expect):
            problems.append(f"doesn't start with {expect!r}")
        if len(value) < 40:
            problems.append(f"looks short ({len(value)} chars) — pasted incompletely?")

        status = "; ".join(problems) if problems else "looks right"
        print(f"  {name:<20} {len(value)} chars, starts {value[:7]}…  → {status}")

    describe("ANTHROPIC_API_KEY", config.ANTHROPIC_API_KEY, "sk-ant-")
    describe("OPENAI_API_KEY", config.OPENAI_API_KEY, "sk-")
    if config.FISH_API_KEY:
        describe("FISH_API_KEY", config.FISH_API_KEY, "")
    print()


def check_claude() -> bool:
    if not config.ANTHROPIC_API_KEY:
        print("🧠 Claude (brain): нет ключа в .env  → добавьте ANTHROPIC_API_KEY")
        return False
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        client.messages.create(
            model=config.BRAIN_MODEL,
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}],
        )
        print("🧠 Claude (brain): ✅ ключ работает")
        return True
    except Exception as error:  # noqa: BLE001 — friendly report, not a crash
        reason = _classify(error)
        if reason == "rejected":
            print("🧠 Claude (brain): ❌ ключ ОТКЛОНЁН — неверный или устаревший ключ")
        elif reason == "no_credit":
            print("🧠 Claude (brain): ⚠️ ключ верный, но НЕТ КРЕДИТОВ — пополните баланс на console.anthropic.com")
        elif reason == "not_found":
            print(f"🧠 Claude (brain): ⚠️ ключ работает, но модель '{config.BRAIN_MODEL}' недоступна")
        else:
            print(f"🧠 Claude (brain): ⚠️ не удалось связаться с Claude ({type(error).__name__})")
        return False


def check_openai() -> bool:
    if not config.OPENAI_API_KEY:
        print("👂 Whisper (ears): нет ключа в .env  → добавьте OPENAI_API_KEY")
        return False
    try:
        import openai

        client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        client.models.list()  # cheap call that just proves the key authenticates
        print("👂 Whisper (ears): ✅ ключ работает")
        return True
    except Exception as error:  # noqa: BLE001
        reason = _classify(error)
        if reason == "rejected":
            print("👂 Whisper (ears): ❌ ключ ОТКЛОНЁН — неверный или устаревший ключ")
        elif reason == "no_credit":
            print("👂 Whisper (ears): ⚠️ ключ верный, но НЕТ КРЕДИТОВ — пополните баланс на platform.openai.com")
        else:
            print(f"👂 Whisper (ears): ⚠️ не удалось связаться с OpenAI ({type(error).__name__})")
        return False


def check_voice() -> bool:
    """Actually make the voice say something.

    This used to print "🗣️ Голос: fish настроен" whenever a key was present —
    which is a statement about the .env file, not about the voice. A key can be
    present and still be refused, out of credit, or pointed at a voice ID that
    no longer exists, and every one of those looks identical from here. The app
    then answers with a 503 and the person sees «не слышит».

    So: say two words for real, through the same code path the app uses. It
    costs a fraction of a cent and it is the only version of this check that
    can be trusted.
    """
    from app import tts

    if not config.tts_configured():
        print("🗣️ Голос: пусто → браузер озвучит бесплатно (для MVP это нормально).")
        return True  # not an error: the client speaks instead

    provider = config.TTS_PROVIDER
    try:
        audio = asyncio.run(tts.synthesize("Проверка связи."))
        if not audio:
            print(f"🗣️ Голос ({provider}): ⚠️ ответил пустотой — звука нет")
            return False
        print(f"🗣️ Голос ({provider}): ✅ говорит ({len(audio) // 1024} КБ)")
        return True
    except Exception as error:  # noqa: BLE001 — friendly report, not a crash
        reason = _classify(error)
        if reason == "rejected":
            print(f"🗣️ Голос ({provider}): ❌ ключ ОТКЛОНЁН — неверный или устаревший")
        elif reason == "no_credit":
            print(f"🗣️ Голос ({provider}): ⚠️ ключ верный, но НЕТ КРЕДИТОВ — пополните баланс")
        elif reason == "not_found":
            print(f"🗣️ Голос ({provider}): ⚠️ такого голоса нет — проверьте ID голоса в .env")
        else:
            print(f"🗣️ Голос ({provider}): ⚠️ не отвечает")

        # The provider's own words. Whatever the guess above, THIS is the fact.
        print(f"           {error}")

        # The voice is the one part with a spare. The ears and the brain each
        # have a single supplier, so a broken one has to be fixed; the voice
        # does not — OpenAI speaks with the same key that already listens. Say
        # so right here, because this is the moment someone is stuck.
        if provider != "openai" and config.OPENAI_API_KEY:
            print()
            print("   Не чините это сейчас — у голоса есть запасной:")
            print("       python switch_voice.py openai")
            print("   Это тот же ключ, которым он уже вас слышит.")
        return False


def main() -> None:
    venv_report()
    shape_report()
    print("Проверяю ключи (сами ключи не показываю)…\n")
    brain_ok = check_claude()
    ears_ok = check_openai()
    voice_ok = check_voice()

    print()
    if brain_ok and ears_ok and voice_ok:
        print("✅ Всё готово — откройте http://localhost:8000 и поговорите с Бобом.")
    else:
        print("Исправьте пункт(ы) с ❌/⚠️ выше и запустите проверку снова.")


if __name__ == "__main__":
    main()

"""The language of the conversation — Russian, or English (COMPANION_LANGUAGE).

Everything the companion is told and says was written in Russian first, and
tuned there turn by turn against measurements. English came on 2026-10-02:
the owner could not hear the brains apart through the Russian voices —
«change everything to English» — and asked that it be done properly, not as
Russian rules with «speak English» at the bottom: «everything must be well
optimized for English».

So every Russian text that reaches a conversation has its English twin beside
it, written for English rather than translated word for word, and which one is
used is decided HERE, at the moment of use — never at import, so a test or a
rehearsal can switch the language and see the other one.

What is NOT in English yet, deliberately: inventing a companion (matchmaker),
the intake and the reading's writer, the diary — none of them speaks during a
conversation (docs/ENGLISH.md).
"""

from __future__ import annotations

from typing import TypeVar

from . import config

T = TypeVar("T")


def english() -> bool:
    """Is the conversation in English?"""
    return (config.LANGUAGE or "").strip().lower().startswith("en")


def pick(ru: T, en: T) -> T:
    """The Russian or the English of the same thing, by the conversation's language."""
    return en if english() else ru


#: Appended to what a model is asked to WRITE for the conversation — facts the
#: scribe keeps, his week, the watcher's note — so that what comes back into
#: the prompt later is in the conversation's language too. The instructions
#: themselves stay Russian: they are read by a model, never heard.
WRITE_IN_ENGLISH = ("\n\nЯЗЫК: разговор идёт по-английски. Всё, что ты пишешь своими "
                    "словами (факты, описания, заметки), пиши по-английски. Ключи JSON и метки, "
                    "которые выбираются из списков выше, оставляй в точности как есть.")


def write_in() -> str:
    """The language line for a model that writes something the companion will read."""
    return WRITE_IN_ENGLISH if english() else ""

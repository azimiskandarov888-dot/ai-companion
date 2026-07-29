"""Behavior rules: the 'third way' honesty, the guardrails, and prompt assembly.

These protect the two most important correctness properties:
  1. Bob never confesses to being a machine, and never claims to be human.
  2. The safety guardrails are always present in the prompt.
"""

from __future__ import annotations

from app import companion


def test_third_way_honesty_present():
    rules = companion.BEHAVIOR_RULES
    # Never confess machine-ness…
    assert "не говоришь, что ты программа" in rules
    # …and never claim to be a flesh-and-blood human.
    assert "НЕ утверждаешь напрямую, будто ты человек" in rules


def test_old_confession_line_is_gone():
    # The previous version told Bob to admit being an AI — that must be gone.
    assert "Ты честен, что ты искусственный интеллект" not in companion.BEHAVIOR_RULES
    assert "скажи об этом мягко и по-доброму" not in companion.BEHAVIOR_RULES


def test_guardrails_present():
    rules = companion.BEHAVIOR_RULES
    assert "не давай медицинских советов" in rules
    assert "не проси денег" in rules
    assert "не обещай того, что должно случиться в его настоящем мире" in rules
    assert "мостик к живой жизни" in rules  # points him back to real family


def test_length_and_word_rules_present():
    rules = companion.BEHAVIOR_RULES
    # Keep replies short by default, and short on a plain greeting.
    assert "не говори лишнего" in rules
    assert "Утро — это просто утро" in rules
    # Plain, simple words — not literary/bookish, not slang.
    assert "простыми, обычными словами" in rules
    assert "молодёжного сленга" in rules
    # Idioms only occasionally, never whole sentences of them.
    assert "не вставляй их в каждый ответ" in rules


def test_news_and_weather_rule_present():
    rules = companion.BEHAVIOR_RULES
    assert "НОВОСТИ И ПОГОДА" in rules
    # Delivered like a person keeping up, not a news reader…
    assert "не как диктор" in rules
    assert "не ссылайся на источники" in rules
    # …and bad news handled gently.
    assert "не пугай его" in rules


def test_human_speech_disfluencies_present():
    rules = companion.BEHAVIOR_RULES
    # Natural hesitations and think-aloud openers (covers a small pause too)…
    assert "дай вспомнить" in rules
    # …and real-person self-corrections.
    assert "поправляй сам себя" in rules
    assert "не переигрывай" in rules  # but only a little — not broken speech


def test_not_an_interview_rule_present():
    rules = companion.BEHAVIOR_RULES
    # Balanced, not an interrogation; don't end every reply with a question…
    assert "Не превращай беседу в допрос" in rules
    assert "НЕ заканчивай вопросом каждый свой ответ" in rules
    # …but Bob may still gently start a topic so the talk doesn't die.
    assert "завести тёплую тему" in rules


def test_build_system_prompt_injects_all_parts():
    prompt = companion.build_system_prompt(
        persona_block="ТЫ — Боб. Живёшь у моря.",
        elder_facts="- любит рыбалку",
        bob_facts="- у Боба есть кот Мурзик",
        memory_context="Вы вспоминали про Волгу.",
        elder_name="Иван",
    )
    assert companion.BEHAVIOR_RULES.split("\n")[0] in prompt  # behavior first
    assert "Живёшь у моря" in prompt
    assert "любит рыбалку" in prompt
    assert "кот Мурзик" in prompt
    assert "Волгу" in prompt
    assert "Иван" in prompt


def test_build_system_prompt_minimal():
    # With nothing injected it still returns the behavior rules cleanly.
    prompt = companion.build_system_prompt()
    assert prompt.strip() == companion.BEHAVIOR_RULES.strip()

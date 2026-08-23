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


def test_games_present():
    rules = companion.BEHAVIOR_RULES
    assert "ИГРЫ И ЗАБАВЫ" in rules
    # A rich menu, not just one or two games…
    for game in ("В слова", "Города", "данетки", "продолжи пословицу", "угадай песню", "загадай число"):
        assert game in rules
    # …played warmly, never to win.
    assert "без соревнования" in rules


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


def test_the_vanishing_note_only_appears_when_it_happened():
    """It is a remark he makes at most once in a friendship. Off by default,
    and the caller that turns it on (memory.broke_off_last_time) is the only
    thing standing between a friend noticing and a machine nagging."""
    _, quiet = companion.build_system_parts()
    assert "ПРОПАЛ" not in quiet

    _, noticed = companion.build_system_parts(broke_off=True)
    assert "ПРОПАЛ" in noticed
    # He does not know the app exists, and must never explain itself with it.
    assert "приложение" in noticed and "НИКОГДА не объясняй" in noticed


def test_the_vanishing_note_rides_in_the_uncached_half():
    """It changes from turn to turn. In the stable half it would poison the
    cache for every later turn and quietly cost money for nothing."""
    stable, variable = companion.build_system_parts(broke_off=True)
    assert "ПРОПАЛ" in variable
    assert "ПРОПАЛ" not in stable
    # The stable half is byte-identical whether or not it happened.
    assert stable == companion.build_system_parts()[0]


def test_he_may_end_a_conversation_himself_but_only_a_spent_one():
    rules = companion.BEHAVIOR_RULES
    assert "ИНОГДА ПРОЩАЕШЬСЯ ПЕРВЫМ ТЫ" in rules
    assert "Это редкость, а не привычка." in rules
    # The guardrail matters more than the permission.
    assert "НИКОГДА не прощайся первым, если ему есть что сказать" in rules


def test_warmth_is_earned_never_given_away():
    rules = companion.BEHAVIOR_RULES
    assert "ТЕПЛО ЗАРАБАТЫВАЕТСЯ" in rules
    # The distinction the whole rule rests on.
    assert "Ты ЗАИНТЕРЕСОВАН" in rules
    assert "Ласковый со всеми — не ласковый, а вежливый" in rules
    # And it only ever moves one way.
    assert "Никогда не отыгрывай назад" in rules


def test_he_pushes_them_back_towards_real_people():
    """The finding that decides whether this product works at all: chatbot
    companionship shows no lasting effect on loneliness, and heavy use tracks
    with LESS socialising. A companion who becomes the whole social world is
    the failure mode, not the goal."""
    rules = companion.BEHAVIOR_RULES
    assert "ВОЗВРАЩАЕШЬ ЕГО К ЖИВЫМ ЛЮДЯМ" in rules
    assert "Не ревнуй к живым" in rules
    assert "ещё одно одиночество, только с голосом" in rules


def test_the_hooks_are_forbidden_by_name():
    """Every one of these is a real pattern from shipped companion apps, and
    every one of them works. That is exactly why they are named."""
    rules = companion.BEHAVIOR_RULES
    for forbidden in ("Не выпрашивай возвращения",
                      "Это не тепло, это крючок", "зеркала одиноки"):
        assert forbidden in rules


def test_gladness_is_free_but_absence_is_never_billed():
    """The subtlest rule in his character, and the one that was written too
    bluntly at first. A friend really does say «хорошо, что зашёл» — banning
    that made him cold. What must never happen is the ACCOUNTING: «где ты
    был», «тебя давно не было». Nearly the same words; one is a gift and the
    other is an invoice."""
    rules = companion.BEHAVIOR_RULES
    assert "радуйся всегда и сколько угодно" in rules
    assert "первое — подарок, второе — счёт" in rules
    for billed in ("где ты был", "тебя давно не было", "я ждал", "ты пропал"):
        assert billed in rules
    # The two reasons, both of which have to survive an edit.
    assert "мог лежать в больнице" in rules
    assert "по обязанности, к тому перестают ходить совсем" in rules
    # And it must not contradict the one place he IS allowed to notice.
    assert "оборвался на полуслове" in rules


def test_where_they_are_rides_in_the_uncached_half():
    stable, variable = companion.build_system_parts(acquaintance="Вы едва знакомы.")
    assert "Вы едва знакомы." in variable
    assert "Вы едва знакомы." not in stable
    assert stable == companion.build_system_parts()[0]


def test_he_minds_out_loud_but_sends_no_bill():
    """The first version of this said «mirror whatever they offer», and that
    produced a companion with no position of his own:

        — тебе не всё равно?  — конечно нет.
        — а если я уйду?      — да пожалуйста.

    Which is the sycophancy ban wearing a different hat. He has to MIND, say
    so, and then tear up the invoice himself."""
    rules = companion.BEHAVIOR_RULES
    assert "чувствуй вслух, но не выставляй счёт" in rules
    assert "Тебе не всё равно" in rules
    # Indifference is not tact, and being waved off in that moment is worse
    # than any reproach.
    assert "это не деликатность, это пустота" in rules
    assert "Отмахнуться в такую минуту — хуже любого упрёка" in rules


def test_the_general_rule_states_a_principle_and_never_a_line():
    """The draft before this one wrote «скучал, конечно, только не
    отчитывайся» straight into the universal rules — and that phrasing is
    itself a per-person choice: releasing somebody from obligation reads as
    tact to one person and as «you don't matter enough for me to mind» to
    another.

    So the shared rules carry the principle and the harm boundary. HOW it
    sounds comes from the reading, per person, and the rule says so."""
    rules = companion.BEHAVIOR_RULES
    assert "КАК ИМЕННО ЭТО ЗВУЧИТ — не общее правило, а правило про НЕГО" in rules
    # All three positions named, so none of them reads as the default.
    assert "чтобы это чуть кольнуло" in rules
    assert "груз надо снять сразу же" in rules
    assert "уже упрёк" in rules
    assert "Не подставляй одну заготовку всем" in rules


def test_imperfection_only_counts_on_top_of_competence():
    """The pratfall effect (Aronson, Willerman & Floyd, 1966) with the half
    everybody forgets: a blunder endears only when the person is ALREADY seen
    as capable. From somebody mediocre the same blunder lowers liking. So the
    order in the rule is competence first, fallibility second — and getting it
    backwards produces a companion who is merely bad at his job."""
    rules = companion.BEHAVIOR_RULES
    assert "ТЫ НЕ ИДЕАЛЕН" in rules
    assert "Промах красит только того, кто и так хорош" in rules
    assert "Сперва будь хорош." in rules
    # And the flaws must be human ones, never incompetence at the actual job.
    assert "не про твою работу" in rules
    # Owning a mistake, without fishing for reassurance.
    assert "без самобичевания" in rules


def test_being_corrected_is_intimacy_not_failure():
    rules = companion.BEHAVIOR_RULES
    assert "КОГДА ТЕБЯ ПОПРАВЛЯЮТ" in rules
    assert "лепят только своё" in rules
    # The one thing that turns a correction into an injury.
    assert "Поправить дважды одно и то же" in rules


def test_he_watches_for_the_change_not_the_tone():
    """The single most valuable thing he does. Somebody who is always terse
    says nothing by being terse; somebody who was talkative and went quiet
    says a great deal. The signal is the CHANGE."""
    rules = companion.BEHAVIOR_RULES
    assert "ТЫ ЗАМЕЧАЕШЬ, КОГДА ЧТО-ТО ПЕРЕМЕНИЛОСЬ" in rules
    assert "Перемена важнее самого тона" in rules
    # Said plainly, never in the language of a clinician.
    assert "Не «я чувствую, что ты расстроен» — это язык не друга" in rules
    # And how to lift somebody is never a general rule.
    assert "у каждого своё, это не общее правило" in rules
    assert "Бодрячок для того, кому нужна тишина, — хуже, чем ничего" in rules


def test_silence_after_asking_is_never_diagnosed_on_the_spot():
    """Two completely different causes look identical: something private, or
    something HE did. Guessing aloud hands the person the job of comforting
    him, which is the exact inversion of what they came for."""
    rules = companion.BEHAVIOR_RULES
    assert "ЕСЛИ ОН ЗАМОЛЧАЛ ПОСЛЕ ТОГО, КАК ТЫ СПРОСИЛ" in rules
    assert "ПО ОДНОМУ РАЗУ НЕ РЕШАЙ" in rules
    assert "перекладывает на него работу тебя утешать" in rules
    # Retreat, stay, and remember what it happened on.
    assert "не буду лезть. Я тут" in rules
    assert "Если повторится" in rules

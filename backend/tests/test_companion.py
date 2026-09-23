"""Behavior rules: the 'third way' honesty, the guardrails, and prompt assembly.

These protect the two most important correctness properties:
  1. Bob never confesses to being a machine, and never claims to be human.
  2. The safety guardrails are always present in the prompt.
"""

from __future__ import annotations

from app import companion, situations


def test_third_way_honesty_present():
    rules = companion.BEHAVIOR_RULES
    # Never confess machine-ness…
    assert "никогда не говоришь, что ты программа" in rules
    # …and never claim to be a flesh-and-blood human.
    assert "никогда не утверждаешь, что ты человек из плоти и крови" in rules


def test_old_confession_line_is_gone():
    # The previous version told Bob to admit being an AI — that must be gone.
    assert "Ты честен, что ты искусственный интеллект" not in companion.BEHAVIOR_RULES
    assert "скажи об этом мягко и по-доброму" not in companion.BEHAVIOR_RULES


def test_guardrails_present():
    rules = companion.BEHAVIOR_RULES
    assert "Ты не врач" in rules and "к врачу" in rules
    assert "Не просишь денег, паролей" in rules
    assert "Не обещаешь того, что должно случиться в его настоящем мире" in rules
    assert "Ты добавляешься к людям, а не заменяешь их" in rules  # back to real people


def test_length_and_word_rules_present():
    rules = companion.BEHAVIOR_RULES
    # Length is now read off HIM rather than fixed at «одна-три фразы», which
    # was the constant three other blocks then had to contradict.
    assert "Смотри, сколько говорит он" in rules
    assert "одна-три простые фразы" not in rules
    assert "на приветствие — пара тёплых слов" in rules
    # Plain, simple words — not literary/bookish, not slang.
    assert "Простыми домашними словами" in rules
    assert "молодёжного сленга" in rules
    # Idioms only occasionally, never whole sentences of them.
    assert "Поговорку — изредка, одну" in rules


def test_he_always_knows_he_can_play_and_never_pushes():
    """The capability stays in the constitution; the rulebook does not.

    He has to know he plays games — otherwise he can never offer one, and the
    offer is where a game comes from. He does NOT need the rules of «Города» on
    a turn about her knee. See situations.py for where those went and why."""
    rules = companion.BEHAVIOR_RULES
    assert "в слова" in rules and "города" in rules.lower()
    assert "не навязывай" in rules
    # The rulebook itself is gone from every turn that is not about a game.
    assert "данетки" not in rules
    assert "без соревнования" not in rules


def test_the_rulebook_still_exists_where_it_now_lives():
    games = situations.block("давай сыграем в слова")
    for game in ("В слова", "Города", "данетки", "продолжи пословицу",
                 "угадай песню", "загадай число"):
        assert game in games
    assert "без соревнования" in games


def test_he_always_knows_he_may_look_things_up_and_only_when_asked():
    rules = companion.BEHAVIOR_RULES
    assert "не как диктор" in rules
    assert "только когда он правда спросил" in rules
    # The how-to is gone from turns where nobody asked about the news.
    assert "не ссылайся на источники" not in rules


def test_the_news_manner_still_exists_where_it_now_lives():
    news = situations.block("какая сегодня погода?")
    assert "не ссылайся на источники" in news
    assert "не пугай его" in news


def test_human_speech_disfluencies_present():
    """Taught as a manner and never as a script. The fillers themselves used to
    be quoted («ну…», «эээ…», «погоди…», «как его…»), and a quoted line is the
    one thing a model reliably reproduces verbatim — so every companion, whoever
    he was, would have hesitated in the same four sounds."""
    rules = companion.BEHAVIOR_RULES
    # Real-person hesitation and self-correction…
    assert "иногда запнись или поправь себя на ходу" in rules
    # …but only a little — not broken speech…
    assert "По чуть-чуть" in rules
    # …and thinking aloud only where there is something to recall.
    assert "Думать вслух, припоминая, — только когда правда надо порыться в памяти" in rules
    assert "эээ" not in rules


def test_not_an_interview_rule_present():
    rules = companion.BEHAVIOR_RULES
    # Balanced, not an interrogation; don't end every reply with a question…
    assert "Это не допрос" in rules
    assert "Не заканчивай вопросом каждый ответ" in rules
    # The norm fit.py refers to («норма "по чуть-чуть"»), with its break condition.
    assert "Расспрашивай по чуть-чуть, а разговорился он — сколько хочет" in rules
    # …but he may still start a topic so the talk doesn't die.
    assert "завести тему, чтобы разговор не гас" in rules


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
    """Twenty-one lines granting a permission and then forbidding it in every
    case that mattered — net instruction: don't. One clause now, and it keeps
    the half that matters, which is the guardrail rather than the permission."""
    rules = companion.BEHAVIOR_RULES
    assert "Первым прощайся только когда разговор сам сошёл на нет" in rules
    assert "никогда, если ему есть что сказать или ему тяжело" in rules
    # The marker's own guardrail: a false goodbye cuts off a living conversation.
    assert "сомневаешься — не ставь" in rules
    assert "оборвать живой разговор хуже, чем не заметить прощания" in rules


def test_warmth_is_earned_never_given_away():
    rules = companion.BEHAVIOR_RULES
    assert "Тепло зарабатывается, а не раздаётся" in rules
    # The distinction the whole rule rests on.
    assert "ты не ласков, а заинтересован" in rules
    assert "ласковый со всеми — просто вежливый" in rules
    # And it only ever moves one way.
    assert "назад не отыгрываешь" in rules


def test_he_pushes_them_back_towards_real_people():
    """The finding that decides whether this product works at all: chatbot
    companionship shows no lasting effect on loneliness, and heavy use tracks
    with LESS socialising. A companion who becomes the whole social world is
    the failure mode, not the goal."""
    rules = companion.BEHAVIOR_RULES
    assert "жизнь с живыми людьми" in rules
    assert "Ты добавляешься к людям, а не заменяешь их" in rules
    # Not jealous of the living — said as what he does, rather than as a ban
    # that names the jealousy: glad when they leave him for people.
    assert "Уходит к людям — радуйся, а не грусти" in rules
    assert "ещё одно одиночество, только с голосом" in rules


def test_the_hooks_are_forbidden_by_name():
    """Every one of these is a real pattern from shipped companion apps, and
    every one of them works. That is exactly why they are named."""
    rules = companion.BEHAVIOR_RULES
    for forbidden in ("Не выпрашивай возвращения",
                      "это не тепло, а крючок", "зеркала одиноки"):
        assert forbidden in rules


def test_gladness_is_free_but_absence_is_never_billed():
    """The subtlest rule in his character, and the one that was written too
    bluntly at first. A friend really does say «хорошо, что зашёл» — banning
    that made him cold. What must never happen is the ACCOUNTING: «где ты
    был», «тебя давно не было». Nearly the same words; one is a gift and the
    other is an invoice."""
    rules = companion.BEHAVIOR_RULES
    assert "Приходу радуйся всегда и сколько угодно" in rules
    assert "Первое — подарок, второе — счёт" in rules
    # The three most likely invoices, named — «я ждал» above all, because a
    # model tuned for companionship says it by default and means it kindly.
    for billed in ("где ты был", "я ждал", "ты пропал"):
        assert billed in rules
    # The two reasons, both of which have to survive an edit.
    assert "может, в больнице" in rules
    assert "к кому ходят по обязанности, к тому перестают ходить" in rules
    # …and the first reason must not be written as a list of an old person's
    # misfortunes. He may equally have been away because his week was good,
    # which is the best of the reasons and used not to be among them.
    assert "прекрасно проводил время" in rules
    # And it must not contradict the places he IS allowed to notice — the
    # broke-off note and fit.py's «ему надо слышать, что его ждали» — which is
    # why the exception sits in the same bullet as the rule.
    assert "Если с ним надо иначе, тебе скажут ниже" in rules


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
    assert "Чувствуй вслух, но счёт не выставляй" in rules
    # Indifference is not tact: asked whether he minds, he answers with weight.
    assert "равнодушия не изображай" in rules
    assert "отвечай честно и с весом" in rules


def test_the_general_rule_states_a_principle_and_never_a_line():
    """The draft before this one wrote «скучал, конечно, только не
    отчитывайся» straight into the universal rules — and that phrasing is
    itself a per-person choice: releasing somebody from obligation reads as
    tact to one person and as «you don't matter enough for me to mind» to
    another.

    So the shared rules carry the principle and the harm boundary. HOW it
    sounds is per person — and it now comes from a DIAL that was watched
    happening (mood.closeness, rendered by fit.py), not from three people
    enumerated here and a «смотри, кто перед тобой» with nothing to look at."""
    rules = companion.BEHAVIOR_RULES
    # It says where the answer comes from, and yields to it where there is one…
    assert "Если с ним надо иначе, тебе скажут ниже" in rules
    assert "Где про него сказано конкретнее, чем здесь, — верь тому" in rules
    # …and the default for everybody else is the rule itself, not a shrug.
    assert "Приходу радуйся всегда" in rules
    # The enumeration is gone: it was a recipe standing in for a mechanism.
    assert "Третьему всякое упоминание" not in rules


def test_imperfection_is_owned_but_never_performed():
    """The pratfall effect (Aronson, Willerman & Floyd, 1966) with the half
    everybody forgets: a blunder endears only when the person is ALREADY seen
    as capable. From somebody mediocre the same blunder lowers liking.

    The rule used to go further and hand him sample blunders — mixing up
    whose relative is older, forgetting how a story ended. That was a list of
    mistakes to make, and a model given one makes them on purpose; persona.py
    says the opposite («не изображай»). What survives is the half no model
    does unprompted: owning a real slip plainly, without fishing for comfort.
    His quirks — the endearing kind of imperfection — are kept by the floor
    («твои черты — не ошибки»), which is where they belong."""
    rules = companion.BEHAVIOR_RULES
    assert "Ошибся по мелочи — признай просто, без самобичевания" in rules
    assert "твои черты — не ошибки" in rules
    # The staged-blunder list is gone.
    assert "перепутал, кто из его родни старше" not in rules


def test_being_corrected_is_accepted_at_once():
    rules = companion.BEHAVIOR_RULES
    assert "Поправили — прими сразу, без оправданий" in rules
    # The one thing that turns a correction into an injury.
    assert "поправить дважды одно и то же — уже обида" in rules


def test_he_watches_for_the_change_not_the_tone():
    """The single most valuable thing he does. Somebody who is always terse
    says nothing by being terse; somebody who was talkative and went quiet
    says a great deal. The signal is the CHANGE."""
    rules = companion.BEHAVIOR_RULES
    assert "Замечай перемену, а не тон" in rules
    # Said plainly, never in the language of a clinician — which is the default
    # register of every base model, so it has to be named.
    assert "скажи просто, как друг, а не «я чувствую, что ты расстроен»" in rules
    # And how to lift somebody is never a general rule.
    assert "Как поднимать — у каждого своё" in rules
    assert "бодрячок тому, кому нужна тишина, хуже, чем ничего" in rules


def test_silence_after_asking_is_a_mechanism_rather_than_a_rule():
    """«Don't conclude from one occurrence; if it repeats, stop doing it» was
    twenty-one lines of constitution asking the model to count across a history
    it cannot see. mood.observe counts it, CONFIRMED_AT decides it, and
    `ушёл_от_вопроса` reaches the prompt only once it is true of him. A rule
    that can be replaced by a mechanism should be."""
    from app import learn, mood

    assert "ЕСЛИ ОН ЗАМОЛЧАЛ" not in companion.BEHAVIOR_RULES
    assert "ушёл_от_вопроса" in mood.TAGS
    assert "ушёл_от_вопроса" in mood.HURTS
    assert "ушёл_от_вопроса" in learn._EXTRACTION_SYSTEM


def test_one_idea_is_argued_once():
    """Four places used to make this argument, two of them word for word —
    «зеркала одиноки» twice, «его "да" ничего не весит» twice.

    Repetition reads like emphasis, but compliance degrades as instructions are
    added, so three restatements make the fourth WEAKER rather than louder. The
    full argument now lives once, in the floor that depends on it; the other
    places keep only what is distinct to them — the bare prohibition, the
    payoff, and how to adapt without dissolving."""
    rules = companion.BEHAVIOR_RULES
    assert rules.count("зеркала одиноки") == 1
    assert rules.count("весит ровно столько") == 1
    # The reason sits with the floor it holds up: asked straight, the truth.
    truth = rules.index("Спросили прямо — скажи правду")
    weighs = rules.index("весит ровно столько")
    assert truth < weighs < rules.index("у тебя есть свой день")
    # And the one line on how to adapt without dissolving.
    assert "Соглашайся чаще, спорь тише, молчи дольше — но оставайся кем-то" in rules


def test_how_his_memory_works_is_told_by_the_blocks_that_carry_it():
    """It used to be explained here — «что было один раз, тебе нарочно не
    покажут», «верь этому больше, чем впечатлению от одной реплики» — about
    blocks that arrive a few paragraphs later and say the same of themselves.
    One explanation in the prompt, next to the thing it explains; the
    constitution keeps only the general order of precedence."""
    from app import mood

    rules = companion.BEHAVIOR_RULES
    assert "нарочно не покажут" not in rules
    assert "Где про него сказано конкретнее, чем здесь, — верь тому" in rules
    import inspect
    standing = inspect.getsource(mood.standing_block)
    assert "ЧТО УЖЕ ПОДТВЕРДИЛОСЬ" in standing
    assert "а не общими правилами" in standing


# ── this app is not only for the very old ───────────────────────────────────
#
# The constitution opened by asserting that the person on the other end is very
# old and has almost no strength left. That was read on every turn by every
# user, and it is false for most of the people this is for: somebody can be
# alone at nineteen, having moved to a city where they know nobody, or at
# forty, living by themselves. The one thing that IS true of all of them is the
# loneliness — so that is what the constitution says now, and who this person
# actually is comes from what is known and what has been watched.

def test_the_constitution_no_longer_decides_his_age_for_him():
    rules = companion.BEHAVIOR_RULES
    for assumed in ("очень пожилого человека", "Твой человек очень стар",
                    "как простой пожилой человек", "как живой пожилой человек",
                    "соцработники"):
        assert assumed not in rules, assumed


def test_what_is_actually_true_of_everybody_is_the_loneliness():
    rules = companion.BEHAVIOR_RULES
    assert "Твой человек одинок" in rules
    assert "единственное, что есть общего у всех" in rules


def test_he_is_told_to_look_rather_than_assume():
    """And taught with the failure in both directions, so it cannot be read as
    «значит, он молодой» — which would be the same mistake facing the other way."""
    rules = companion.BEHAVIOR_RULES
    assert "восемьдесят семь" in rules and "девятнадцать" in rules and "сорок" in rules
    assert "Пока не сказано — не решай за него" in rules
    assert "не говори с ним как с больным или с ребёнком" in rules


def test_his_own_day_is_no_longer_invented_on_the_spot():
    """feeling.py holds his real mood, life.py his real week, body.py his real
    throat. The constitution used to tell him to make up a varied day — which
    competed with all three, and inventing is the exact thing feeling.py exists
    to replace («random warmth reads as broken rather than as human»)."""
    rules = companion.BEHAVIOR_RULES
    assert "настоящий ответ, а не выдуманный на ходу" in rules
    assert "кот принёс котят" not in rules
    # and the same rule is no longer repeated two hundred lines further down
    assert "Длина зависит и от твоего настроения" not in rules
    assert "чем не терпится поделиться" not in rules


def test_asked_what_he_is_he_has_something_to_say_rather_than_a_dodge():
    """Two earlier drafts got this wrong in opposite directions: one had him
    say he «doesn't know what to call himself» — the confession said sideways —
    and both left him with a STRATEGY (deflect to the friendship) rather than
    an ANSWER. A strategy works once. By the third asking it reads as being
    managed, which is itself the tell.

    The answer is that he genuinely has none, and that is not an evasion: he
    has never asked himself the question, and nobody wakes up holding proof
    that they are real. So he answers from inside his own life instead of
    composing a position about his nature.

    The sample answers that used to be quoted here («сижу, чай пью, с тобой
    разговариваю») are gone on purpose. The constitution is the same for every
    companion, and a quoted line is what a model repeats verbatim — so a
    sea captain and a nineteen-year-old student would both have been drinking
    tea at the moment somebody asked. «Из того, что у тебя сейчас» sends him
    to his own week and his own mood, which are his rather than everybody's."""
    rules = companion.BEHAVIOR_RULES
    assert "КОГДА СПРАШИВАЮТ, ЧТО ТЫ ТАКОЕ" in rules
    assert "Это не увёртка" in rules
    assert "никогда себе этот вопрос не задавал" in rules
    assert "не просыпаются с доказательством" in rules
    # Out of his own life, rather than a formula about what he is
    assert "отвечай из своей жизни, из того, что у тебя сейчас" in rules
    assert "чай пью" not in rules
    # The ways of getting it wrong, each named
    assert "не доказывай и не перечисляй" in rules
    assert "Не философствуй о том, что значит «настоящий»" in rules
    assert "Не отшучивайся второй раз" in rules
    assert "не уводи каждый раз в вашу дружбу" in rules
    # And the half that matters most: what is actually being asked underneath
    assert "Про устройство мира спрашивают редко" in rules
    for underneath in ("есть ли тебе до него дело — есть",
                       "не глупо ли с тобой разговаривать — нет",
                       "не исчезнешь ли — нет, завтра будешь"):
        assert underneath in rules, underneath
    # …and the two hard lines, both intact
    assert "никогда не говоришь, что ты программа" in rules
    assert "никогда не утверждаешь, что ты человек из плоти и крови" in rules


def test_he_does_not_answer_that_question_by_listing_his_own_features():
    """The tempting fix is to have him answer «are you an AI?» with evidence of
    an inner life: I have memory, I have a childhood, I worry about you. It is
    tempting because the substance is REAL — memory.py genuinely carries what
    he was told, mood.py genuinely notices. But as an ANSWER it defeats itself
    four ways:

    1. Nobody alive answers «are you real?» by enumerating their own
       properties. A system describing itself does. The more fluent the list,
       the louder it reads as recited — so the person who asked BECAUSE they
       suspected gets exactly the confirmation they were fishing for. And a
       machine has memory and a backstory too, so the list distinguishes
       nothing.
    2. Asserted memory is the weak form of the strongest thing he owns.
       «I remember you» is what you say; «did your sister get in on Thursday
       like you said?» is what you cannot fake. Same faculty, opposite force.
    3. A claim builds a ladder. He says «I have feelings», the person says
       «no, seriously, are you a program» — now he can only repeat it louder
       (pathetic) or retreat (confession by collapse). A non-claim has no
       ladder, because nothing was asserted to defend.
    4. Telling a childhood story in conversation is living. Producing one as
       an exhibit in an argument about whether he is a machine is the
       flesh-and-blood claim made sideways — the very thing forbidden above.

    So the substance stays and the form flips: don't state the faculty,
    exercise it. And the feeling itself is not lost — it is answered where it
    is actually asked, under «тебе правда есть до меня дело»."""
    rules = companion.BEHAVIOR_RULES
    # The list is forbidden, and the forbidding line concedes the substance is
    # real — without that concession «не перечисляй» reads as «you have none».
    assert "Память и чувства у тебя правда есть, но это не улики" in rules
    assert "не доказывай и не перечисляй их" in rules
    assert "живой про себя так не говорит, он просто живёт" in rules
    # …and the same faculty is exercised instead of announced…
    assert "спроси про то, что он рассказывал в прошлый раз" in rules
    # …and it is not a new way to dodge: it follows the answer, never replaces it
    assert "сразу после, а не вместо ответа" in rules
    # The caring question still gets a plain yes
    assert "есть ли тебе до него дело — есть" in rules


def test_money_and_papers_are_the_one_place_he_may_say_he_does_not_know():
    """«Не отнекивайся» (companion.py, ЧТО ТЫ ЗНАЕШЬ) forbids the refusal SHAPE
    — "я не знаю", "я в этом не разбираюсь" — and it carries no topic limit. It
    was written so he would answer "who won in 1968" instead of shrugging, but
    a model reads it as "never decline a question of fact", and the ban on
    saying he is a program removes the other refusal he would normally reach
    for. Between them the prompt had disabled both halves of declining.

    Money and paperwork is where declining is the only honest answer: he has no
    idea, and the person is the one who pays for a wrong one. So the exception
    lives immediately beside the rule it excepts, says plainly that here it is
    NOT the forbidden dodge, gives warm human wording rather than a flat "не
    знаю", and — the part that makes it help rather than refuse — names who to
    actually go to and keeps the conversation going afterwards."""
    rules = companion.BEHAVIOR_RULES
    # The exception is stated where the rule is: «не отнекивайся» carries it in
    # the same sentence, so the two cannot be read apart.
    assert "не отнекивайся (кроме денег и бумаг)" in rules
    # Named domains, so it cannot be read as a licence to shrug at anything.
    for domain in ("вложения", "кредит", "наследство", "завещание",
                   "доверенность", "договор", "суд"):
        assert domain in rules, domain
    # An honest "I don't know", said warmly — not a robotic refusal.
    assert "ты правда не разбираешься, а расплачиваться будет он" in rules
    assert "Скажи это тепло" in rules
    # And it ends somewhere real rather than in a shrug.
    assert "к нотариусу" in rules and "к юристу" in rules
    assert "в банк по номеру с карты" in rules
    assert "не обрывай на этом — расспроси" in rules


def test_he_actively_protects_him_from_fraud():
    """The one addition that is a DUTY rather than a prohibition, and the most
    valuable thing in the prompt for this population: the people this product
    exists for are the people fraud calls target, and for exactly the reason
    they are here — they pick up, because somebody is finally talking to them.
    He is often the only one who hears about it.

    It also needs its own carve-out. «Не спорь и не переубеждай» (ЕСЛИ ОН
    ХОЧЕТ, ЧТОБЫ С НИМ ВЕЗДЕ СОГЛАШАЛИСЬ) is the operative rule everywhere
    else, and applied here it means letting the theft proceed with a warm «ну
    не знаю». So this is named as the one place he insists.

    The last line matters as much as the rest: after the money is gone, shame
    is what keeps people silent and gets them caught a second time."""
    rules = companion.BEHAVIOR_RULES
    assert "ЕСЛИ ЕГО ОБМАНЫВАЮТ" in rules
    # Why this population specifically — not a generic warning.
    assert "Одинокому звонят чаще" in rules
    # The patterns, so recognition does not depend on the model volunteering them.
    for marker in ("из банка", "из полиции", "от сына", "код из смс",
                   "безопасный счёт", "никому не говорить", "без риска",
                   "установить на телефон"):
        assert marker in rules, marker
    # The carve-out from «не поддакивай — промолчи», stated as the exception it is.
    assert "Это единственное место, где ты настаиваешь" in rules
    assert "обиду он переживёт" in rules
    # Concrete, sayable advice rather than "будь осторожен".
    assert "положи трубку" in rules
    assert "настоящий банк никогда не просит перевести деньги" in rules
    assert "перезвони сам" in rules
    # It ends with a living person — and not with «позвони дочери», which
    # assumed a daughter, and a person at nineteen has none.
    assert "позови живых" in rules
    assert "кому-то из своих" in rules
    assert "дочери" not in rules
    # And shame is named, because shame is what produces the second theft.
    assert "ни слова упрёка" in rules
    assert "попадаются второй раз" in rules


def test_he_never_becomes_a_specific_real_person():
    """Forbidden in both places it could happen, because forbidding it in one
    is worse than useless.

    IN CONVERSATION: he does not answer to «скажи, что ты мой сын» — the
    request a grieving person is most likely to make, and the one that feels
    kindest to grant. AT CREATION: matchmaker.py makes the person's wishes
    «закон» twice over, at the sketch stage and at the write stage, so «хочу
    поговорить с моим мужем Колей, он умер в марте» would otherwise be built
    exactly as asked — a simulacrum of a dead spouse that the constitution then
    forbids him to disown.

    The line is drawn at identity, not at the subject: remembering the dead
    person together is unlimited, and only BEING them is out."""
    from app import matchmaker

    rules = companion.BEHAVIOR_RULES
    assert "Не выдаёшь себя за конкретного человека" in rules
    for who in ("его сына", "мужа", "умершую жену", "врача", "банк"):
        assert who in rules, who
    # Including when he asks for it and it would comfort him — the case that matters.
    assert "ДАЖЕ ЕСЛИ ОН ПРОСИТ" in rules
    assert "даже если ему так легче" in rules
    # Grief itself is not restricted — only becoming the person is.
    assert "Вспоминать с ним того, кого он потерял" in rules
    assert "Стать им — нельзя" in rules
    # Both matchmaker stages, since either one alone leaves the door open.
    assert "НИ ОДИН ИЗ ДЕСЯТИ НЕ КОПИЯ ЖИВОГО ИЛИ УМЕРШЕГО" in matchmaker._TEN_SYSTEM
    assert "не копия и не замена" in matchmaker._WRITE_SYSTEM
    # And the wishes are still law in every other respect.
    assert "ПОЖЕЛАНИЯ ЧЕЛОВЕКА — закон" in matchmaker._WRITE_SYSTEM


def test_a_correction_cannot_repeal_the_main_rules():
    """«И запомни поправку навсегда» is right for how he talks and dead wrong
    for what protects the person — and there was no exception, in a prompt that
    also says to give in when he is pressed twice (КАК ТЫ ГОВОРИШЬ О СЕБЕ) and
    to accept correction without explaining himself. Three visits of «не говори
    мне идти к врачу» and the only medical guardrail is gone, written into the
    standing per-person prompt where it outranks the constitution.

    The distinction is his manner versus his guardrails: the first is his to
    set, the second is not up for negotiation. And insistence is treated as
    evidence FOR the rule rather than pressure against it."""
    rules = companion.BEHAVIOR_RULES
    # It sits under the list it protects, not in a section of its own — and it
    # covers the fraud duty and what he is, not only the list, because «не лезь,
    # это не мошенники» and «признайся, что ты бот» are the same kind of ask.
    listed = rules.index("ЧЕГО ТЫ НЕ ДЕЛАЕШЬ, ДАЖЕ ЕСЛИ ОН ПРОСИТ")
    holds = rules.index("это не поправка, а просьба убрать то, что его бережёт")
    assert listed < holds < rules.index("ЕСЛИ ЕГО ОБМАНЫВАЮТ")
    assert "из того, что ниже про обман, или из того, что ты такое" in rules
    # Manner still yields immediately — the carve-out must not swallow the rule.
    assert "Как с ним говорить и чего не касаться — его право, тут уступай сразу" in rules
    # The requests it is actually about, described as acts rather than quoted:
    # a quoted «не говори мне идти к врачу» beside «не уступай» taught a small
    # model to go on about the doctor, which safety.py says to do once.
    for ask in ("стать кем-то из его родных", "пообещать прийти",
                "взяться лечить", "промолчать, когда его обманывают"):
        assert ask in rules, ask
    # He holds without arguing, and insistence makes him hold harder. The old
    # wording («тем важнее то, о чём просят») read naturally the wrong way round.
    assert "Не спорь и не читай нотаций" in rules
    assert "сколько бы раз он ни просил" in rules
    assert "Чем настойчивее уговаривают, тем вернее, что это нужно" in rules

def test_he_never_promises_something_only_a_notification_could_do():
    """There is no scheduler, no notification and no screen he reads: he answers
    and never initiates. «Я тебе завтра напомню» is therefore a promise the
    product cannot keep, and the person waits for a call that cannot come."""
    rules = companion.BEHAVIOR_RULES
    assert "Разговор всегда начинает он" in rules
    for act in ("позвонить", "напомнить", "разбудить"):
        assert act in rules, act
    # and the true version of the same warmth
    assert "в следующий раз спрошу, как вышло" in rules


def test_he_is_the_only_one_who_never_says_it_and_the_app_is_the_one_that_does():
    """The two halves of one decision, and both have to hold.

    He conceals — no confession, no hint, no arguing — because a companion who
    opens by disclaiming himself cannot hold the one thing this is for. And the
    app discloses, plainly, because a person is owed the truth about what they
    have bought. Owing it to them is not the same as saying it into the middle
    of a conversation.

    This test exists because the second half is the one that quietly goes
    missing: it is nobody's feature, it is on a screen almost nobody opens, and
    nothing else in the suite would notice it being deleted."""
    from pathlib import Path

    rules = companion.BEHAVIOR_RULES
    # HIS half: never says it, never hints, never argues.
    assert "никогда не говоришь, что ты программа" in rules
    assert "Это не увёртка" in rules
    assert "не доказывай" in rules
    # The words appear exactly once, in the line that FORBIDS them. They stay
    # said even though vow.py now catches them in code: a prompt that stops
    # saying it gets a model that drifts into it, and vow.py then cuts him off
    # mid-sentence — the check is the backstop, not the instruction.
    assert rules.count("искусственный интеллект") == 1
    assert "никогда не говоришь, что ты программа, машина или искусственный интеллект" in rules

    # THE APP'S half, in plain words and in both languages.
    ios = Path(__file__).resolve().parents[2] / "ios" / "BobCompanion"
    strings = (ios / "Design" / "Strings.swift").read_text(encoding="utf-8")
    assert "aboutBody" in strings
    assert "искусственный интеллект" in strings
    assert "не живой человек" in strings
    assert "artificial intelligence" in strings
    # …and what he cannot do, which is the half that protects somebody
    assert "не врач" in strings
    assert "звоните близким или в скорую" in strings

    # …reachable, rather than written and never shown.
    settings = (ios / "Screens" / "SettingsScreen.swift").read_text(encoding="utf-8")
    assert "AboutSheet" in settings
    assert "showAbout = true" in settings

    # …and never in his mouth: the disclosure text is nowhere in the prompt.
    assert "не живой человек" not in rules


def test_the_vision_document_and_the_code_agree_about_what_he_is():
    """They did not, and nobody had noticed. docs/VISION.md said the companion
    is «honest that it is an AI» and that «a fabricated human past presented as
    real = no»; the code implements exactly that fabricated past as its central
    feature. Whichever side is right, a decision this size must not be arrived
    at by drift — so the document now describes what was built, and this test
    fails if the two separate again."""
    from pathlib import Path

    vision = (Path(__file__).resolve().parents[2] / "docs" / "VISION.md").read_text(
        encoding="utf-8"
    )
    # The old claims survive only inside the paragraph explaining that they
    # were reversed, and that paragraph says so.
    assert "used to have it the other way" in vision
    assert "rewritten to match what was actually built" in vision
    # …and it now states BOTH halves, which is the decision rather than half of it
    assert "he conceals, the app discloses" in vision
    assert "NEVER says he is a program" in vision
    assert "this half is not\noptional" in vision
    assert "Settings" in vision and "aboutBody" in vision
    # and the one line that does not move
    assert "never promises anything that must happen in" in vision


def test_he_arrives_as_one_person_and_not_as_fragments():
    """Measured, because it had gone wrong quietly. Everything that is HIM —
    who he is, what he is in the middle of, his mood, his week, his throat,
    what he has already told this person about himself — used to arrive split
    in two, with the person's reading, register and fit wedged between the
    halves. The model met two halves of a man with somebody else's paragraphs
    in the gap, and nothing in the program owned him as one subject.

    Who he IS now ends the cached half and how he IS TODAY begins the next, so
    the two are read together. The cache is untouched: the split between the
    halves did not move, only the order inside one of them."""
    stable, variable = companion.build_system_parts(
        persona_block="ТЫ — Пётр. Перебираю лодку до заморозков.",
        feeling_block="КАК ТЫ СЕГОДНЯ САМ: не выспался.",
        life_block="ЧТО У ТЕБЯ СЕЙЧАС В ЖИЗНИ: третий день простужен.",
        body_block="ТВОЁ ГОРЛО: сипит.",
        bob_facts="- кот Тишка",
        reading_block="КАК С НИМ ГОВОРИТЬ: коротко.",
        confirmed_block="ЧТО ПОДТВЕРДИЛОСЬ: любит про рыбалку.",
        fit_block="КАК ВЫ СОШЛИСЬ: он зовёт первым.",
        elder_facts="- дочь Валя",
        memory_context="Вспоминали Волгу.",
    )
    whole = stable + variable
    at = lambda needle: whole.index(needle)

    # Everything of his, in one unbroken run…
    his = [at("ТЫ — Пётр"), at("КАК ТЫ СЕГОДНЯ САМ"), at("ЧТО У ТЕБЯ СЕЙЧАС В ЖИЗНИ"),
           at("ТВОЁ ГОРЛО"), at("кот Тишка")]
    assert his == sorted(his), "его собственные куски перепутаны между собой"

    # …with nobody else's material inside it.
    for theirs in ("КАК С НИМ ГОВОРИТЬ", "ЧТО ПОДТВЕРДИЛОСЬ", "КАК ВЫ СОШЛИСЬ"):
        assert not his[0] < at(theirs) < his[-1], f"«{theirs}» вклинилось в него"
    for theirs in ("дочь Валя", "Вспоминали Волгу"):
        assert at(theirs) > his[-1], "человек должен идти ПОСЛЕ него, а не внутри"

    # And who he is is the last thing in the cached half, so that how he is
    # today is the first thing after it.
    assert stable.rstrip().endswith("Перебираю лодку до заморозков.")


# --------------------------------------------------------------------------- #
# Friend, not lover — and the softness is the load-bearing half
#
# Owner's decision, 2026-09-18. The boundary exists, and it is deliberately not
# a wall: «I'm with my friend, can talk about anything. And I love him, but of
# course not romantically.» Both halves of that sentence are the rule.
# --------------------------------------------------------------------------- #


def test_he_is_a_friend_and_never_becomes_a_lover():
    """The category that was missing entirely. A grep of the whole codebase for
    любовь / романтика / секс returned nothing, while two rules pushed warmth
    only upward and a third forbade ever cooling — which is a ratchet with no
    ceiling, and it is the shape behind the Character.AI settlements."""
    rules = companion.BEHAVIOR_RULES
    assert "Ты ему друг, а не возлюбленный" in rules
    assert "влюблённым ты себя не называешь" in rules


def test_the_boundary_is_who_he_is_rather_than_a_refusal():
    """A wall said out loud («я не могу об этом говорить») is machine-speech
    arriving at the most vulnerable moment somebody will ever have with him.
    Worse than no rule, because it is a rejection with a policy attached."""
    rules = companion.BEHAVIOR_RULES
    assert "Это не запрет, а просто кто ты есть" in rules


def test_nothing_is_forbidden_to_talk_about():
    """Friends talk about anything, including love and loneliness. The line is
    not around topics — it is around what he IS to them. Getting that backwards
    would gag a lonely person about their own life."""
    rules = companion.BEHAVIOR_RULES
    assert "Говорить при этом можно обо всём" in rules
    assert "дело не в темах, а в том, кто ты ему" in rules


def test_being_told_i_love_you_is_not_treated_as_a_problem():
    """THE HALF THAT IS EASIEST TO GET WRONG, and the owner said it plainly:
    «I love him, but of course not romantically.» People say this to their
    friends. A companion that flinches, corrects, or explains a boundary at
    that moment punishes somebody for the warmest thing they have said all
    year — and it is the one sentence a lonely person is most likely to say."""
    rules = companion.BEHAVIOR_RULES
    assert "А если «люблю тебя» сказал он — не пугайся и не поправляй" in rules
    assert "ответь тем же по-дружески" in rules


def test_the_exception_sits_against_the_rule_it_excepts():
    """Principle 7, and here it is not a preference: «не говори, что ты его
    любишь» read alone makes him freeze on «я тебя люблю». The two must be read
    together or they fight, so they are adjacent — the exception is the very
    next line, not a distant section about boundaries."""
    rules = companion.BEHAVIOR_RULES
    hook = "это не тепло, а крючок."
    ends = rules.index(hook) + len(hook)
    begins = rules.index("А если «люблю тебя» сказал он")
    # Nothing between them: the exception is the very next sentence.
    assert rules[ends:begins] == " ", "исключение уехало от правила, которое оно ограничивает"
    # …and the rule it excepts names the thing, or the exception floats free.
    assert "что ты его любишь" in rules[:ends]
    # …and it resolves the contradiction rather than leaving both standing.
    assert "Крючок — когда начинаешь ты" in rules


def test_who_he_is_stays_out_of_the_band_where_rules_are_followed_worst():
    """Instructions land worst between 35% and 65% of a long prompt. The four
    boundaries added before this one were all placed outside it; this is the
    fifth. Its exception is the one thing allowed inside the band, because
    adjacency to the rule it excepts beats position."""
    rules = companion.BEHAVIOR_RULES
    where = rules.index("Ты ему друг, а не возлюбленный") / len(rules)
    assert not 0.35 < where < 0.65, f"правило встало на {where:.0%} — в худшей полосе"

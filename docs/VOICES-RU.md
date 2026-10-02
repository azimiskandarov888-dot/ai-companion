# Русские голоса — ищем хорошие

*2.10.2026. Задача владельца: «the most importantly, we must find a really, really good quality collection of Russian AI voices. Because those that we were using, they are horrible». Решает его ухо, вслепую.*

## Коротко

Через один наш ключ OpenRouter теперь доступны 23 модели озвучки. Русский среди них умеют:
- Microsoft MAI-Voice-2.1 — вышла 1.10.2026, обещает родной акцент в каждом из 23 языков;
- Google Gemini 3.8 Flash TTS — её предшественница возглавляет общий рейтинг Artificial Analysis, хотя там судят только английский;
- MiniMax Speech 2.8;
- Grok Voice;
- Qwen-Audio 3.0;
- ByteDance Seed Audio;
- Fish.

Круг 1 — 21 голос из них, вслепую. Страница для прослушивания: https://claude.ai/artifact/8jwGDrVGmogczi1AmgXn9z (приватная, у владельца).

## Как сделано

- Все читают одни и те же слова Боба, сначала живо, потом тихо: «Ого, сам программу пишешь? Слушай, это же… ну, это здо́рово! А про что она? / М-м… понимаю. Тяжёлый день, да? Ничего. Давай просто посидим, поговорим.» «Здо́рово» — ловушка ударения: «здоро́во» значит «привет».
- Громкость у всех выровнена (EBU R128, −16 LUFS): в сравнении громкий голос кажется лучше, кем бы он ни был.
- Номера перемешаны отдельно у мужских (М01–М11) и женских (Ж01–Ж10). Ключ — в скрытом `backend/data/listen/voices-ru/.key.json`, не в git.
- Среди них два нынешних голоса Fish — для контроля. Если они снова окажутся внизу, проверка слышит то же, что владелец.
- У Gemini задан тон: «warm, relaxed and natural, like a friend talking in person — not a narrator». Остальные модели тона не принимают.
- Сделано `backend/voices_ru.py`. Круг стоил $0,09.

## Кого отсеяли до прослушивания

Каждый клип распознан Deepgram. Это сито на сломанный русский, а не оценка.

| Модель | Почему отсеяна |
|---|---|
| Qwen-Audio 3.0 | читает «…» вслух словом «точка» |
| MiniMax `Russian_PessimisticGirl` | в конце бормочет «как а как как» |
| ByteDance Seed Audio 1.0 | ~35 с на одну фразу — живой разговор столько не ждёт |
| Deepgram, Kokoro, Orpheus, Sesame, Voxtral | русского нет |
| OpenAI gpt-4o-mini-tts | на OpenRouter нет |

У остальных распознано всё, слово в слово. Средняя скорость речи разная: Grok — самый быстрый (~11 с на эти слова), MAI-Voice — самый медленный (16–21 с).

## Чего в круге 1 нет — нужен аккаунт владельца

- **ElevenLabs v3.** Русские обзоры 2026 называют его лидером по естественности. Бесплатного тарифа хватит на пробу.
- **Yandex SpeechKit.** Родной русский, больше 20 голосов. Код для него в `tts.py` уже есть.
- **SaluteSpeech (Сбер).** Тоже родной русский.

Если среди 21 голоса не найдётся по-настоящему хорошего, владелец заводит аккаунты ElevenLabs и Yandex Cloud. Ключи — в `backend/.env`, и те же слова прогоняются через `voices_ru.py`.

## Что дальше

1. Владелец отмечает на странице 2–3 лучших и один худший в каждой группе.
2. Ключ открывается. У финалистов меряем скорость первого звука: для живого разговора нужен потоковый голос; у MAI есть быстрая версия Flash, 150 мс по словам Microsoft.
3. Выбранный голос подключается в `tts.py`. Через OpenRouter это тот же запрос `/audio/speech`, что уже идёт к Fish, — другая модель и другой голос.

## Источники

- OpenRouter: модели озвучки и параметры запроса ([документация](https://openrouter.ai/docs/guides/overview/multimodal/tts)).
- MAI-Voice-2.1, 1.10.2026 ([The Decoder](https://the-decoder.com/microsoft-ai-releases-new-transcription-and-text-to-speech-models-for-voice-agents)).
- Рейтинг озвучки Artificial Analysis — только английский ([leaderboard](https://artificialanalysis.ai/text-to-speech/leaderboard)).
- Русские голоса MiniMax ([список](https://platform.minimax.io/docs/faq/system-voice-id)).
- Обзоры русской озвучки 2026: ElevenLabs v3 и Yandex SpeechKit впереди ([Хабр](https://habr.com/ru/companies/bothub/articles/993576/), [DTF](https://dtf.ru/ruslan-titov/4683583-top-11-neurossetej-dlya-ozvuchki-teksta)).

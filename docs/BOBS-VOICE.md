# The robot's voice

Rendered once, bundled with the app, never synthesised on a phone again.

```
python3 tools/bob_voice.py --audition     # hear three strengths, pick one
python3 tools/bob_voice.py                # render all 45 lines
```

## Why it's baked rather than spoken live

The robot's lines are fixed. Everyone who installs the app hears the same
forty-five sentences, so there is no reason to synthesise them on a phone,
forever, for every person.

That also lifts the constraint that shapes the *companion's* voice. His has to
be cheap — he talks all day, every day, to everybody. This is forty-five
sentences, one time, for the whole product. Use the best thing you can get.

## Why no text-to-speech will give you a robot

Because they're all trained to sound like a person, and the good ones succeed.
That's the wrong target. **GLaDOS is not a synthetic voice — she is Ellen
McLain, processed.** The machine quality lives in the effects, not the source.

So `bob_voice.py` takes the deepest, flattest voice available and then:

| step | what it does |
|---|---|
| `asetrate` → `atempo` | drops pitch **and formants together**, then puts the duration back. This is what makes it a bigger *thing*, not a person slowed down. A pitch shifter keeps the formants and just sounds like a cold. |
| `chorus` | two of it, slightly detuned. The single most "not one throat" effect there is, and it costs no intelligibility. |
| `tremolo` | amplitude modulation at 26 Hz — under the pitch range of speech, so it reads as machine rather than as a note. This is the buzz most people mean by "robotic". |
| `highpass` + `lowpass` | out of a speaker set into a wall, not out of a mouth. |
| `acompressor` | flat and unbothered. A robot doesn't get louder when it cares. |
| `aecho` | a small hard room. |
| `loudnorm` | every line at the same loudness — nothing gives away a stitched-together script faster. |

### Intelligibility is the constraint

The listener is eighty and being told where to tap. `heavy` sounds better in a
demo and loses words in a kitchen. **Ship `standard`** unless you've listened
to `heavy` on a phone speaker, at arm's length, with a kettle going.

## Which base voice

Any deep, calm, *even* male voice. The processing supplies the character, so
what you want from the source is flatness, not expression.

- **Yandex `zahar`** — the default. Lowest of the standard voices, the keys are
  already in `backend/.env`, and forty-five lines costs pennies.
- **Yandex `ermil`** — brighter. Fine, less imposing.
- **ElevenLabs** — better raw material if you want it; `--provider elevenlabs
  --voice <id>`. Since this is a one-off render, the price is irrelevant.

**Do not use the voice the companion uses.** If the robot and the friend sound
alike, the one job this robot exists to do — being obviously not him — is gone.
`filipp` is the companion's default, so the robot must not have it.

## Installing the files

`tools/bob_voice.py` writes into `ios/BobCompanion/Resources/Voice/`. Getting
them into the app needs:

```
cd ios && xcodegen generate
```

…and then **setting your Development Team again in Xcode by hand** —
regenerating clears it. This is the one time that's worth doing.

## If a file is missing

The line falls back to the phone's synthesiser (`SpeechVoice.Character.machine`
— lower pitch, the compact voice). Nothing breaks, nothing looks wrong. So the
files can go in a few at a time, in any order, and a line you rewrite later
just speaks itself until you re-render.

## The slugs

On each step in `Strings.swift`: `voiceover: "bob-come-03"`.

| prefix | which part |
|---|---|
| `bob-come-*` | who he is, the taps, the goodbye lesson, Siri |
| `bob-coy-*` | «имя я знаю, но не скажу» |
| `bob-vocal-*` | the walk through Settings |
| `bob-name-*` | coming back after they've met |
| `bob-bye-*` | his last words on the arrival screen |
| `bob-again-*` | opening the sheet from Settings |
| `bob-other-*` | back tap, side button, Control Centre |

The two opening lines have no slug: they're `silent: true` — shown before the
robot has been woken — so a recording of them could never play.

## Names are shown, never spoken

Every line is recordable months before anybody's friend exists, because **no
line contains a name.** The steps that involve one show it on screen and speak
around it — «три раза скажите слово, которое написано ниже» — carried by
`RobotStep.spoken`, which overrides what is said without changing what is read.

Two reasons, and the second is the one that matters. A synthesiser mispronounces
Russian stress; and getting somebody's *name* wrong is not a small error, it's
the machine fumbling the one word a person minds most.

The robot says so itself, which turns the limitation into the joke:

> «И да — имена я вслух не читаю. Поставлю ударение не туда, а потом окажется,
> что для кого-то это было принципиально. Смотрите на экран.»

## Reading it, if a person ever does record it

Dry. Competent. Faintly bored. An announcement system in a very old research
facility that has had a long day.

- **The joke is never on the listener** — it's on Bob, or on the procedure.
- **The instructions are flat.** «Универсальный доступ», «Голосовые команды»,
  «Настроить» — plainly and slowly. Character lives in the sentences either
  side, never in the steps.
- Slower than feels natural. The listener is eighty.

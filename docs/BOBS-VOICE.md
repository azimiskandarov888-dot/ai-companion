# Recording Bob yourself

The setup robot reads its lines with the phone's synthesiser. Every line can
be replaced with a real recording, one at a time, in any order. A missing file
is not a failure — that line simply falls back to the synthesiser — so you can
record five lines tonight and the rest next month.

## How

1. Record each line as a separate file.
2. Name it after the line's slug: `bob-come-03.m4a`.
3. Put the files in `ios/BobCompanion/Resources/Voice/`.
4. Run `xcodegen generate` **and set your Development Team again in Xcode** —
   regenerating wipes it. This is the one time it's worth doing.

`.m4a`, `.mp3`, `.caf`, `.wav` and `.aiff` all work. No conversion needed.

## The slugs

They're in `Strings.swift`, on each step: `voiceover: "bob-come-03"`.

| prefix | which part |
|---|---|
| `bob-touch-*` | the two silent lines before the first tap |
| `bob-come-*` | who he is, the taps, the goodbye lesson, Siri |
| `bob-coy-*` | «имя я знаю, но не скажу» |
| `bob-vocal-*` | the walk through Settings |
| `bob-name-*` | coming back after they've met |
| `bob-bye-*` | his last words on the arrival screen |
| `bob-again-*` | opening the sheet from Settings |
| `bob-other-*` | back tap, side button, Control Centre |

**Four lines have no slug on purpose**: `bob-vocal-03`, `bob-vocal-04`,
`bob-name-02` and `bob-name-04` are missing from the numbering because those
lines say the friend's name out loud — «скажите «Фёдор» три раза» — and his
name isn't known when you'd be recording. Those four stay synthesised.

If that bothers you, the fix is to rewrite them so the name is only ever on
screen and never spoken («скажите три раза слово, которое видите ниже»). Say
the word and I'll do it — it needs the step to carry two texts instead of one.

## How to read them

Dry. Competent. Faintly bored. Not warm, not sorry, not selling anything.
Think of an announcement system in a very old research facility that has had a
long day.

Two things to keep:

- **The joke is never on the listener.** It's on Bob, or on the procedure.
  These are lonely, tired, elderly people; a machine that mocks them is the
  last straw.
- **The instructions are flat.** «Универсальный доступ», «Голосовые команды»,
  «Настроить» — say those plainly and slowly. The character lives in the
  sentences either side of them, never in the steps themselves.

Slower than feels natural. The listener is eighty.

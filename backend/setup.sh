#!/usr/bin/env bash
# Один запуск — и tryout.py готов слушать. Для macOS и Linux.
#
#     bash setup.sh
#
# Делает три вещи, каждую только если её ещё не сделали: своё окружение
# Питона, библиотеки, пустой .env под ключ. Запускать повторно безопасно.
#
# И одну вещь делает всегда, раньше всего остального: проверяет, не лежит ли
# настоящий ключ в .env.example. Тот файл СПЕЦИАЛЬНО не спрятан от git (строка
# `!.env.example` в .gitignore) — он образец, он обязан уезжать на GitHub.
# Ключ, попавший туда вместо .env, уедет вместе с ним и станет чужим. Правило
# «не клади ключ в образец» ничего не держит; проверка — держит. Владелец
# положил его именно туда с первого раза, потому что файл на виду и открывается
# первым.
set -e
cd "$(dirname "$0")"

# ── ключ в образце ─────────────────────────────────────────────────────────
#
# Отличаем настоящий ключ от образца по длине. .env.example СУЩЕСТВУЕТ ради
# строк вида `ANTHROPIC_API_KEY=sk-ant-...`, и первая версия этой проверки
# ловила именно их — останавливала установку на совершенно чистом файле, то
# есть делала обратное тому, зачем написана. Настоящий ключ любого провайдера
# от тридцати знаков (самый короткий, Fish, ровно тридцать два), образец
# короткий и почти всегда с многоточием. Двадцать пять — с запасом между ними.
if [ -f .env.example ]; then
  leaked=$(awk -F= '
    /^[[:space:]]*[A-Z_]+_?API_KEY[[:space:]]*=/ {
      value = substr($0, index($0, "=") + 1)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      if (length(value) >= 25 && index(value, "...") == 0) print $1
    }' .env.example)
  if [ -n "$leaked" ]; then
    echo
    echo "  СТОП. В .env.example лежит настоящий ключ:"
    echo "$leaked" | sed 's/^/      /'
    echo
    echo "  Этот файл уезжает на GitHub — так и задумано, он образец."
    echo "  Перенеси ключ в .env (он на GitHub не уедет), а в .env.example"
    echo "  оставь пустое место после знака ="
    echo
    echo "  Если уже успел закоммитить и запушить — считай ключ чужим:"
    echo "  заведи новый и удали старый."
    echo
    exit 1
  fi
fi

# ── Питон ──────────────────────────────────────────────────────────────────
# На macOS команда только `python3`: голого `python` там нет со времён Catalina.
if ! command -v python3 >/dev/null 2>&1; then
  echo
  echo "  Питона нет. Поставь так:"
  echo "      brew install python3"
  echo "  Нет brew — возьми с python.org/downloads"
  echo
  exit 1
fi

[ -d .venv ] || { echo "Делаю окружение..."; python3 -m venv .venv; }

echo "Ставлю библиотеки..."
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt

# ── .env ───────────────────────────────────────────────────────────────────
[ -f .env ] || { echo "OPENROUTER_API_KEY=" > .env; echo "Создал .env"; }

echo
if grep -qE '^[[:space:]]*OPENROUTER_API_KEY[[:space:]]*=[[:space:]]*[^[:space:]]' .env; then
  echo "  Всё готово. Запускай:"
  echo
  echo "      .venv/bin/python tryout.py --talk"
else
  echo "  Осталось одно: ключ."
  echo
  echo "  Возьми на openrouter.ai/keys и впиши в файл .env вот так:"
  echo
  echo "      OPENROUTER_API_KEY=sk-or-твой-ключ"
  echo
  echo "  Потом запускай:"
  echo
  echo "      .venv/bin/python tryout.py --talk"
fi
echo

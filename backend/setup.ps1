# Один запуск — и tryout.py готов слушать. Для Windows.
#
#     powershell -ExecutionPolicy Bypass -File setup.ps1
#
# Делает три вещи, каждую только если её ещё не сделали: своё окружение
# Питона, библиотеки из requirements.txt, пустой .env под ключ. Запускать
# повторно безопасно — он не ломает то, что уже стоит.
#
# И одну вещь он делает всегда: проверяет, не лежит ли ключ в .env.example.
# Это не придирка. .env.example СПЕЦИАЛЬНО не спрятан от git (см. строку
# `!.env.example` в .gitignore) — он образец, он обязан уезжать на GitHub.
# Ключ, который туда попал, уедет вместе с ним и станет чужим. Правило «не
# клади ключ в образец» ничего не держит; проверка — держит.
#
# ── ЭТОТ ФАЙЛ ОБЯЗАН ЛЕЖАТЬ В UTF-8 С BOM. НЕ СНИМАЙТЕ BOM ────────────────
#
# Windows PowerShell 5.1 — тот, что стоит в Windows из коробки, — читает .ps1
# без BOM в системной однобайтовой кодировке, а не в UTF-8. Русский текст
# превращается в «Р·Р°РєРѕРјРјРёС‚РёС‚СЊ», и на этом всё бы и кончилось, если бы дело
# было только в виде. Но мусор попадает и внутрь кавычек: разбор строки
# уезжает, и файл перестаёт быть разбираемым вообще — четыре ошибки про
# незакрытые скобки в местах, где всё закрыто.
#
# Так это и случилось у владельца при первом же запуске. Отсюда два правила:
# BOM в начале файла и строка с OutputEncoding ниже. Первое нужно, чтобы файл
# ПРОЧИТАЛСЯ, второе — чтобы то, что он печатает, было ВИДНО.

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
Set-Location $PSScriptRoot

# ── ключ в образце: проверяем раньше всего остального ──────────────────────
$example = ".env.example"
if (Test-Path $example) {
    $leak = Select-String -Path $example -Pattern '^\s*[A-Z_]*API_KEY\s*=\s*\S' -Quiet
    if ($leak) {
        Write-Host ""
        Write-Host "  СТОП. В .env.example лежит настоящий ключ." -ForegroundColor Red
        Write-Host ""
        Write-Host "  Этот файл уезжает на GitHub — так и задумано, он образец."
        Write-Host "  Перенеси ключ в .env (он на GitHub не уедет), а в .env.example"
        Write-Host "  оставь пустое место после знака ="
        Write-Host ""
        Write-Host "  Если уже успел закоммитить и запушить — считай ключ чужим:"
        Write-Host "  заведи новый на openrouter.ai/keys, а старый удали."
        Write-Host ""
        exit 1
    }
}

# ── Питон ──────────────────────────────────────────────────────────────────
# `python3` на Windows — это заглушка, которая открывает Microsoft Store.
# Настоящие команды — `py` и `python`, именно в таком порядке.
$py = $null
foreach ($try in @("py", "python")) {
    if (Get-Command $try -ErrorAction SilentlyContinue) { $py = $try; break }
}
if (-not $py) {
    Write-Host ""
    Write-Host "  Питона нет." -ForegroundColor Red
    Write-Host "  Поставь с python.org/downloads и ОБЯЗАТЕЛЬНО отметь галочку"
    Write-Host "  'Add Python to PATH' на первом экране установщика."
    Write-Host ""
    exit 1
}

if (-not (Test-Path ".venv")) {
    Write-Host "Делаю окружение..." -ForegroundColor Cyan
    & $py -m venv .venv
}

$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

Write-Host "Ставлю библиотеки..." -ForegroundColor Cyan
& $venvPy -m pip install --quiet --upgrade pip
& $venvPy -m pip install --quiet -r requirements.txt

# ── .env ───────────────────────────────────────────────────────────────────
if (-not (Test-Path ".env")) {
    "OPENROUTER_API_KEY=" | Out-File -FilePath ".env" -Encoding utf8
    Write-Host "Создал .env" -ForegroundColor Cyan
}

$hasKey = Select-String -Path ".env" -Pattern '^\s*OPENROUTER_API_KEY\s*=\s*\S' -Quiet
Write-Host ""
if ($hasKey) {
    Write-Host "  Всё готово. Запускай:" -ForegroundColor Green
    Write-Host ""
    Write-Host "      .venv\Scripts\python.exe tryout.py --talk"
} else {
    Write-Host "  Осталось одно: ключ." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Возьми на openrouter.ai/keys и впиши в файл .env вот так:"
    Write-Host ""
    Write-Host "      OPENROUTER_API_KEY=sk-or-твой-ключ"
    Write-Host ""
    Write-Host "  Потом запускай:"
    Write-Host ""
    Write-Host "      .venv\Scripts\python.exe tryout.py --talk"
}
Write-Host ""

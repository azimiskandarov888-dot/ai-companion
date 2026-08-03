#!/usr/bin/env bash
#
# Copy the eight graded photographs into the app's asset catalog.
#
#   ./install-photos.sh                 # looks in ./out
#   ./install-photos.sh ~/Desktop/out   # or wherever you put them
#
# If it can't find them it goes looking, then says exactly what's missing
# instead of "no such file".

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"        # ios/design/grade
CATALOG="$(cd "$HERE/../.." && pwd)/BobCompanion/Resources/Assets.xcassets"

NAMES=(1-signin 2-payment 3-story 4-meet 5-companion 6-diary 7-account 8-settings)

# ── Where are the photographs? ────────────────────────────────────────────────

SRC="${1:-$HERE/out}"

have_them() {
    [ -d "$1" ] && [ -n "$(ls "$1"/1-signin.* 2>/dev/null)" ]
}

if ! have_them "$SRC"; then
    echo "Not in $SRC — looking around your Mac…"
    found=$(find "$HOME" -maxdepth 7 \( -name "1-signin.jpg" -o -name "1-signin.png" \) 2>/dev/null \
            | grep -v "/Library/" | head -1)
    if [ -n "$found" ]; then
        SRC="$(dirname "$found")"
        echo "Found them in $SRC"
    else
        echo
        echo "✗  I can't find the graded photographs anywhere."
        echo
        echo "   Make them first:"
        echo "     cd \"$HERE\""
        echo "     python3 grade.py"
        echo
        echo "   (Your five original photos go in $HERE/in first.)"
        exit 1
    fi
fi

# ── Copy them in ──────────────────────────────────────────────────────────────

if [ ! -d "$CATALOG" ]; then
    echo "✗  The app isn't here: $CATALOG"
    echo "   Run 'git pull' in the repository first."
    exit 1
fi

copied=0
missing=()

for n in "${NAMES[@]}"; do
    file=$(ls "$SRC/$n".jpg "$SRC/$n".jpeg "$SRC/$n".png 2>/dev/null | head -1)
    if [ -z "$file" ]; then
        missing+=("$n")
        continue
    fi
    dest="$CATALOG/$n.imageset"
    mkdir -p "$dest"
    rm -f "$dest/$n".jpg "$dest/$n".jpeg "$dest/$n".png
    cp "$file" "$dest/$n.${file##*.}"

    # Contents.json has to name the file that's actually there.
    cat > "$dest/Contents.json" <<JSON
{
  "images" : [
    {
      "filename" : "$n.${file##*.}",
      "idiom" : "universal"
    }
  ],
  "info" : {
    "author" : "xcode",
    "version" : 1
  }
}
JSON
    copied=$((copied + 1))
done

# ── Say what happened ─────────────────────────────────────────────────────────

echo
echo "Copied $copied of 8 into the app."

if [ ${#missing[@]} -gt 0 ]; then
    echo
    echo "Missing from $SRC:"
    for n in "${missing[@]}"; do echo "   $n"; done
    echo
    echo "Re-run the grader to make them:"
    echo "   cd \"$HERE\" && python3 grade.py"
    exit 1
fi

echo "All eight are in. Next:  cd \"$(cd "$HERE/../.." && pwd)\" && xcodegen generate"

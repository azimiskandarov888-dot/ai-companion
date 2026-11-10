#!/bin/bash
# Verification gate (verification loop).
#   verify.sh gate  — Stop hook: while code in backend/ ios/ tools/ has uncommitted
#                     changes without a reviewer PASS, the session may not finish.
#                     After 3 blocked tries it hands over to the owner.
#   verify.sh pass  — run by the reviewer agent ONLY, after it wrote PASS.
# State lives in .claude/verify/ (gitignored).

root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$root" || exit 0
dir="$root/.claude/verify"
mkdir -p "$dir"
paths=(backend ios tools)

changes=$(
  git diff HEAD -- "${paths[@]}" 2>/dev/null
  git ls-files -z --others --exclude-standard -- "${paths[@]}" 2>/dev/null \
    | while IFS= read -r -d '' f; do shasum "$f"; done
)
hash=$(printf '%s' "$changes" | shasum | cut -c1-16)

case "$1" in
  pass)
    if [ -z "$changes" ]; then echo "No code changes to mark."; exit 0; fi
    touch "$dir/pass-$hash"; rm -f "$dir/tries"
    echo "PASS recorded for $hash."
    exit 0 ;;
  gate)
    cat >/dev/null  # hook input is not needed
    if [ -z "$changes" ] || [ -f "$dir/pass-$hash" ] || [ -f "$dir/handed-$hash" ]; then
      rm -f "$dir/tries"; exit 0
    fi
    tries=$(cat "$dir/tries" 2>/dev/null || echo 0)
    if [ "$tries" -ge 3 ]; then
      rm -f "$dir/tries"; touch "$dir/handed-$hash"
      echo '{"systemMessage":"Verification gate: 3 tries without a reviewer PASS. Handed over to the owner: tell him plainly what still fails."}'
      exit 0
    fi
    tries=$((tries + 1)); echo "$tries" > "$dir/tries"
    printf '{"decision":"block","reason":"Verification gate (try %s/3): code in backend/, ios/ or tools/ changed and has no reviewer PASS. Run the reviewer agent with the brief, the matching checklist from .claude/checklists/ and the REAL result (test output, screenshots). Fix what fails and review again. If it cannot pass, say so and stop."}\n' "$tries"
    exit 0 ;;
  *) echo "usage: verify.sh gate|pass" >&2; exit 2 ;;
esac

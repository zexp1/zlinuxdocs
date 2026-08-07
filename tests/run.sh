#!/usr/bin/env bash
#
# tests/run.sh — the acceptance suite.
#
# Covers D3 (does the work), D4 (validate goes RED on a broken PDF) and D5
# (fix-headings is idempotent), plus the novice path: no arguments, a wrong
# verb, a file name with spaces and brackets, unicode, degenerate documents,
# and a missing LibreOffice.
#
# Usage:
#   tests/run.sh                 # test the source tree
#   ZLD=zlinuxdocs tests/run.sh  # test the INSTALLED command instead
#
# Exits non-zero if anything failed.
#
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ZLD="${ZLD:-$ROOT/bin/zlinuxdocs}"
# Resolve to an absolute path so the masked-PATH tests below can still find it.
if [ ! -x "$ZLD" ]; then
  ZLD_RESOLVED="$(command -v "$ZLD" 2>/dev/null || true)"
  [ -n "$ZLD_RESOLVED" ] || { echo "tests/run.sh: cannot find the command '$ZLD'" >&2; exit 2; }
  ZLD="$ZLD_RESOLVED"
fi

# Where the example documents live: beside the installed program if we are
# testing an install, otherwise in the source tree.
if [ -n "${ZLD_SAMPLES:-}" ]; then
  S="$ZLD_SAMPLES"
elif [ "$ZLD" = "$ROOT/bin/zlinuxdocs" ] && [ -d "$ROOT/share/samples" ]; then
  S="$ROOT/share/samples"
else
  S="/usr/share/zlinuxdocs/samples"
fi

TMP="$(mktemp -d "${TMPDIR:-/tmp}/zlinuxdocs-tests-XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0
FAILED_NAMES=()

pass() { PASS=$((PASS + 1)); printf 'PASS  %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); FAILED_NAMES+=("$1"); printf 'FAIL  %s\n      %s\n' "$1" "${2:-}"; }

# run <name> <expected-exit> <command...>
run_exit() {
  local name="$1" want="$2"; shift 2
  local out rc
  out="$("$@" 2>&1)"; rc=$?
  if [ "$rc" -eq "$want" ]; then
    pass "$name (exit $rc)"
  else
    fail "$name" "expected exit $want, got $rc: $(printf '%s' "$out" | head -2 | tr '\n' ' ')"
  fi
}

# expect_out <name> <regex> <command...>   (command must also exit 0)
expect_out() {
  local name="$1" pattern="$2"; shift 2
  local out rc
  out="$("$@" 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ]; then
    fail "$name" "exited $rc: $(printf '%s' "$out" | head -2 | tr '\n' ' ')"
  elif printf '%s' "$out" | grep -qE "$pattern"; then
    pass "$name"
  else
    fail "$name" "output did not match /$pattern/: $(printf '%s' "$out" | head -3 | tr '\n' ' ')"
  fi
}

# expect_out_rc <name> <expected-exit> <regex> <command...>
expect_out_rc() {
  local name="$1" want="$2" pattern="$3"; shift 3
  local out rc
  out="$("$@" 2>&1)"; rc=$?
  if [ "$rc" -ne "$want" ]; then
    fail "$name" "expected exit $want, got $rc"
  elif printf '%s' "$out" | grep -qE "$pattern"; then
    pass "$name"
  else
    fail "$name" "output did not match /$pattern/: $(printf '%s' "$out" | head -3 | tr '\n' ' ')"
  fi
}

no_traceback() {
  local name="$1"; shift
  local out
  out="$("$@" 2>&1)"
  if printf '%s' "$out" | grep -q 'Traceback (most recent call last)'; then
    fail "$name" "a Python traceback reached the user"
  else
    pass "$name"
  fi
}

echo "zlinuxdocs test suite"
echo "  command:  $ZLD"
echo "  examples: $S"
echo "  workdir:  $TMP"
echo

# --------------------------------------------------------------------------
echo "--- 0. the program itself"
# --------------------------------------------------------------------------
expect_out "version prints a semantic version" '^zlinuxdocs [0-9]+\.[0-9]+\.[0-9]+$' "$ZLD" --version
expect_out "help lists all six commands" 'inspect' "$ZLD" --help
for v in fix-headings convert validate markers profile; do
  expect_out "help lists $v" "$v" "$ZLD" --help
done
expect_out "bare invocation gives a one-line orientation" 'look inside Word documents' "$ZLD"
expect_out "bare invocation lists the commands" 'fix-headings' "$ZLD"
expect_out "quickstart is a numbered walkthrough" '1\. Work somewhere harmless' "$ZLD" quickstart
expect_out "examples shows real command lines" 'Final Report v2 \(1\)\.docx' "$ZLD" examples
expect_out "samples lists the shipped documents" 'plain-no-headings\.docx' "$ZLD" samples
expect_out "help <verb> works" 'chapter list' "$ZLD" help convert
expect_out "aliases are documented in help" 'ALSO WRITTEN AS' "$ZLD" --help

echo
echo "--- 1. aliases"
expect_out "zlinuxdocs info == inspect" 'Real headings' "$ZLD" info "$S/proper-headings.docx"
expect_out "zlinuxdocs show == inspect" 'Real headings' "$ZLD" show "$S/proper-headings.docx"
expect_out "zlinuxdocs fix == fix-headings" 'promotions' "$ZLD" fix "$S/proper-headings.docx" --dry-run
expect_out "zlinuxdocs repair == fix-headings" 'promotions' "$ZLD" repair "$S/proper-headings.docx" --dry-run
expect_out "zlinuxdocs flags == markers" 'marker' "$ZLD" flags "$S/with-markers.docx"
expect_out "zlinuxdocs todo == markers" 'marker' "$ZLD" todo "$S/with-markers.docx"
expect_out "zlinuxdocs settings == profile" 'Profile:' "$ZLD" settings
expect_out "zlinuxdocs pdf == convert (dry-run)" 'Would convert' "$ZLD" pdf "$S/proper-headings.docx" -o "$TMP/a.pdf" --dry-run
expect_out "zlinuxdocs to-pdf == convert (dry-run)" 'Would convert' "$ZLD" to-pdf "$S/proper-headings.docx" -o "$TMP/a.pdf" --dry-run

echo
echo "--- 2. a wrong verb suggests the right one"
expect_out_rc "'covert' suggests 'convert'" 2 "Did you mean 'convert'" "$ZLD" covert x.docx
expect_out_rc "'inspct' suggests 'inspect'" 2 "Did you mean 'inspect'" "$ZLD" inspct x.docx
expect_out_rc "'validte' suggests 'validate'" 2 "Did you mean 'validate'" "$ZLD" validte x.pdf
expect_out_rc "a wrong verb does not dump the whole help" 2 "The commands are:" "$ZLD" nonsenseverb

echo
echo "--- 3. every verb with no arguments is helpful, not a crash"
for v in inspect fix-headings convert validate markers; do
  expect_out_rc "$v with no file explains what to do" 1 "What to do" "$ZLD" "$v"
  no_traceback "$v with no file shows no traceback" "$ZLD" "$v"
done
expect_out "profile with no arguments still works" 'Profile:' "$ZLD" profile

echo
echo "--- 4. inspect, on every relevant example"
expect_out "inspect finds look-alike headings" 'Look-alikes:     12' "$ZLD" inspect "$S/plain-no-headings.docx"
expect_out "inspect names the repair command" 'zlinuxdocs fix-headings' "$ZLD" inspect "$S/plain-no-headings.docx"
expect_out "inspect finds real headings" 'Real headings:   8' "$ZLD" inspect "$S/proper-headings.docx"
expect_out "inspect counts tables" 'Tables:          2' "$ZLD" inspect "$S/mixed-tables.docx"
expect_out "inspect counts markers" '\[V\] markers:     5' "$ZLD" inspect "$S/with-markers.docx"
expect_out "inspect handles an empty document" 'Paragraphs:      0' "$ZLD" inspect "$S/empty.docx"
expect_out "inspect handles a one-line document" 'Paragraphs:      1' "$ZLD" inspect "$S/one-line.docx"
expect_out "inspect --verbose lists styles" 'Styles in use' "$ZLD" inspect "$S/proper-headings.docx" --verbose
expect_out "inspect refuses a heading in mid-sentence" 'Look-alikes:     12' "$ZLD" inspect "$S/plain-no-headings.docx"

echo
echo "--- 5. fix-headings: the repair, and D5 idempotency"
cp "$S/plain-no-headings.docx" "$TMP/report.docx"
expect_out "dry-run reports what it would promote" 'Would promote 12' "$ZLD" fix-headings "$TMP/report.docx" --dry-run
expect_out "dry-run is readable, not a data dump" 'chapter headings' "$ZLD" fix-headings "$TMP/report.docx" --dry-run
if [ -f "$TMP/report-fixed.docx" ]; then fail "dry-run wrote a file" "it must not"; else pass "dry-run wrote nothing"; fi

expect_out "first run promotes 12 headings" 'Promoted 12' "$ZLD" fix-headings "$TMP/report.docx" -o "$TMP/report-fixed.docx"
expect_out "D5: second run reports 0 promotions" '0 promotions' "$ZLD" fix-headings "$TMP/report-fixed.docx" -o "$TMP/report-fixed2.docx"
expect_out "D5: second run via --dry-run reports 0 promotions" '0 promotions' "$ZLD" fix-headings "$TMP/report-fixed.docx" --dry-run
expect_out "already-correct document reports 0 promotions" '0 promotions' "$ZLD" fix-headings "$S/proper-headings.docx" --dry-run
expect_out "empty document reports 0 promotions" '0 promotions' "$ZLD" fix-headings "$S/empty.docx" --dry-run
expect_out "one-line document reports 0 promotions" '0 promotions' "$ZLD" fix-headings "$S/one-line.docx" --dry-run

echo
echo "--- 6. safety: the tool must not destroy anybody's document"
expect_out_rc "refuses to overwrite an existing output" 1 "will not be overwritten" \
  "$ZLD" fix-headings "$TMP/report.docx" -o "$TMP/report-fixed.docx"
expect_out "--force allows the overwrite" 'Saved' \
  "$ZLD" fix-headings "$TMP/report.docx" -o "$TMP/report-fixed.docx" --force
expect_out_rc "refuses -o pointing at the input" 1 "same as the input" \
  "$ZLD" fix-headings "$TMP/report.docx" -o "$TMP/report.docx"
expect_out_rc "refuses --in-place together with -o" 1 "opposite things" \
  "$ZLD" fix-headings "$TMP/report.docx" --in-place -o "$TMP/other.docx"
expect_out_rc "refuses to write without -o" 1 "will not overwrite your original" \
  "$ZLD" fix-headings "$TMP/report.docx"
cp "$S/plain-no-headings.docx" "$TMP/inplace.docx"
expect_out "--in-place keeps a .bak of the original" '\.bak' "$ZLD" fix-headings "$TMP/inplace.docx" --in-place
if [ -f "$TMP/inplace.docx.bak" ]; then pass "the .bak file really exists"; else fail "the .bak file really exists" "missing"; fi
expect_out_rc "a missing file is explained plainly" 1 "there is no file called" "$ZLD" inspect "$TMP/does-not-exist.docx"
expect_out_rc "a folder instead of a file is explained" 1 "is a folder, not a file" "$ZLD" inspect "$TMP"
printf 'this is not a docx' > "$TMP/fake.docx"
expect_out_rc "a fake .docx is explained plainly" 1 "not a readable Word" "$ZLD" inspect "$TMP/fake.docx"
no_traceback "a fake .docx produces no traceback" "$ZLD" inspect "$TMP/fake.docx"

echo
echo "--- 7. file names with spaces and brackets"
cp "$S/weird name (final) v2.docx" "$TMP/"
expect_out "inspect handles spaces and brackets" 'Look-alikes' "$ZLD" inspect "$TMP/weird name (final) v2.docx"
expect_out "markers handles spaces and brackets" 'marker' "$ZLD" markers "$TMP/weird name (final) v2.docx"
expect_out "fix-headings handles spaces and brackets" 'Promoted' \
  "$ZLD" fix-headings "$TMP/weird name (final) v2.docx" -o "$TMP/weird name (fixed) v2.docx"
if [ -f "$TMP/weird name (fixed) v2.docx" ]; then pass "the output with brackets was created"; else fail "the output with brackets was created" "missing"; fi

echo
echo "--- 8. markers"
expect_out "markers finds all five" 'Found 5 \[V\] marker' "$ZLD" markers "$S/with-markers.docx"
expect_out "markers looks inside tables" 'table row' "$ZLD" markers "$S/with-markers.docx"
expect_out "markers reports the section each is under" 'Under: 1 - Background' "$ZLD" markers "$S/with-markers.docx"
expect_out "markers says so when there are none" 'No \[V\] markers found' "$ZLD" markers "$S/proper-headings.docx"
expect_out "markers --tsv is spreadsheet-ready" '^section[[:space:]]+where[[:space:]]+text' "$ZLD" markers "$S/with-markers.docx" --tsv
expect_out "markers -o writes a file" 'Wrote 5 marker' "$ZLD" markers "$S/with-markers.docx" --tsv -o "$TMP/markers.tsv"
expect_out "markers --marker finds a custom mark" 'No \[TODO\] markers found' "$ZLD" markers "$S/proper-headings.docx" --marker '[TODO]'

echo
echo "--- 9. profile"
expect_out "profile summarises in plain words" 'Paper:' "$ZLD" profile
expect_out "profile is honest about PDF/A" 'NOT VERIFIED' "$ZLD" profile
expect_out "profile --list names the profiles" 'release' "$ZLD" profile --list
expect_out "profile --show draft works" 'Profile:      draft' "$ZLD" profile --show draft
expect_out "profile --raw prints the file" 'house print profile' "$ZLD" profile --raw
expect_out "profile --path prints a path" '\.yaml$' "$ZLD" profile --path
expect_out "profile -o copies it out" 'Copied the print settings' "$ZLD" profile -o "$TMP/mine.yaml"
expect_out_rc "profile rejects an unknown name" 1 "no profile called" "$ZLD" profile --show nosuchprofile

echo
echo "--- 10. convert (needs LibreOffice)"
if command -v soffice >/dev/null 2>&1; then
  expect_out "convert --dry-run writes nothing" 'Nothing was written' \
    "$ZLD" convert "$TMP/report-fixed.docx" -o "$TMP/report.pdf" --dry-run
  expect_out "convert makes a PDF" 'Created' "$ZLD" convert "$TMP/report-fixed.docx" -o "$TMP/report.pdf"
  expect_out_rc "convert refuses to overwrite" 1 "will not be overwritten" \
    "$ZLD" convert "$TMP/report-fixed.docx" -o "$TMP/report.pdf"
  expect_out "convert --force replaces it" 'Created' \
    "$ZLD" convert "$TMP/report-fixed.docx" -o "$TMP/report.pdf" --force
  expect_out "convert --pdfa states its limit" 'NOT verified' \
    "$ZLD" convert "$TMP/report-fixed.docx" -o "$TMP/report-a.pdf" --pdfa
  expect_out "convert --help states the PDF/A limit" 'does NOT prove' "$ZLD" help convert
  expect_out_rc "convert rejects an unknown output format" 1 "does not know how to make" \
    "$ZLD" convert "$TMP/report-fixed.docx" -o "$TMP/report.xyz"
  expect_out "convert handles spaces in the name" 'Created' \
    "$ZLD" convert "$TMP/weird name (fixed) v2.docx" -o "$TMP/weird name out.pdf"
  expect_out "convert makes a PDF from the unicode example" 'Created' \
    "$ZLD" convert "$S/unicode-heavy.docx" -o "$TMP/unicode.pdf"
  expect_out "convert makes a PDF from the table example" 'Created' \
    "$ZLD" convert "$S/mixed-tables.docx" -o "$TMP/tables.pdf"
  # The unrepaired document, converted straight to PDF, is the RED control.
  "$ZLD" convert "$S/plain-no-headings.docx" -o "$TMP/unrepaired.pdf" >/dev/null 2>&1
else
  echo "SKIP  convert tests (LibreOffice is not installed)"
fi

echo
echo "--- 11. convert without LibreOffice names the apt package"
# A PATH that contains everything the program needs EXCEPT soffice. Nothing is
# uninstalled; LibreOffice is simply made unreachable, the way it would be on a
# machine that never had it.
mkdir -p "$TMP/nosoffice"
for t in python3 sh cat sed grep pdfinfo pdftotext qpdf file; do
  p="$(command -v "$t" 2>/dev/null)" && ln -sf "$p" "$TMP/nosoffice/$t"
done
CLEAN_PATH="$TMP/nosoffice"
if command -v soffice >/dev/null 2>&1; then
  if PATH="$CLEAN_PATH" command -v soffice >/dev/null 2>&1; then
    fail "the masked PATH really hides soffice" "soffice is still reachable"
  else
    pass "the masked PATH really hides soffice"
  fi
  out="$(PATH="$CLEAN_PATH" "$ZLD" convert "$TMP/report-fixed.docx" -o "$TMP/x.pdf" 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -q 'apt install libreoffice-writer'; then
    pass "missing LibreOffice names 'sudo apt install libreoffice-writer' (exit $rc)"
  else
    fail "missing LibreOffice names the apt package" "rc=$rc out=$(printf '%s' "$out" | head -3 | tr '\n' ' ')"
  fi
  if printf '%s' "$out" | grep -q 'Traceback'; then
    fail "missing LibreOffice shows no traceback" "traceback leaked"
  else
    pass "missing LibreOffice shows no traceback"
  fi
else
  echo "SKIP  missing-LibreOffice test (soffice is not installed anyway)"
fi

echo
echo "--- 12. validate: D4, observed RED first"
printf 'not a pdf' > "$TMP/broken.pdf"
expect_out_rc "D4: a file that is not a PDF fails" 1 "not a PDF file at all" "$ZLD" validate "$TMP/broken.pdf"
: > "$TMP/zero.pdf"
expect_out_rc "an empty file fails" 1 "empty" "$ZLD" validate "$TMP/zero.pdf"
expect_out_rc "a missing PDF is explained plainly" 1 "there is no file called" "$ZLD" validate "$TMP/nope.pdf"
no_traceback "a broken PDF produces no traceback" "$ZLD" validate "$TMP/broken.pdf"

if [ -f "$TMP/unrepaired.pdf" ]; then
  expect_out_rc "a PDF with no bookmarks fails, and says why" 1 "no bookmarks" "$ZLD" validate "$TMP/unrepaired.pdf"
  expect_out_rc "the bookmark failure names the repair command" 1 "fix-headings" "$ZLD" validate "$TMP/unrepaired.pdf"
  expect_out "--no-bookmarks lets a leaflet through" 'PASS' "$ZLD" validate "$TMP/unrepaired.pdf" --no-bookmarks
fi

if [ -f "$TMP/report.pdf" ]; then
  expect_out "the repaired PDF passes every check" 'RESULT: PASS' "$ZLD" validate "$TMP/report.pdf"
  expect_out "the repaired PDF really has bookmarks" 'Bookmarks: 1[0-9]' "$ZLD" validate "$TMP/report.pdf"
  expect_out "--verbose lists the passing checks too" 'no broken field codes' "$ZLD" validate "$TMP/report.pdf" --verbose
  expect_out "--json is machine-readable" '"ok": true' "$ZLD" validate "$TMP/report.pdf" --json
  expect_out_rc "--json still exits non-zero on failure" 1 '"ok": false' "$ZLD" validate "$TMP/broken.pdf" --json
fi

echo
echo "--- 13. unicode survives the round trip"
expect_out "inspect reads the unicode example" 'Real headings:   6' "$ZLD" inspect "$S/unicode-heavy.docx"
if [ -f "$TMP/unicode.pdf" ] && command -v pdftotext >/dev/null 2>&1; then
  txt="$(pdftotext "$TMP/unicode.pdf" - 2>/dev/null)"
  ok=1
  for probe in "বাংলা" "देवनागरी" "Kokborok" "₹"; do
    printf '%s' "$txt" | grep -q "$probe" || { ok=0; missing="$probe"; }
  done
  if [ "$ok" -eq 1 ]; then
    pass "Bengali, Devanagari, Kokborok and the rupee sign survive conversion"
  else
    fail "unicode survives conversion" "'$missing' is missing or mangled in the PDF text"
  fi
  if printf '%s' "$txt" | grep -q 'Ã\|â€'; then
    fail "no mojibake in the converted PDF" "mojibake markers found"
  else
    pass "no mojibake in the converted PDF"
  fi
fi

echo
echo "--- 14. degenerate documents must not crash anything"
for f in empty.docx one-line.docx; do
  for v in inspect markers; do
    run_exit "$v on $f exits 0" 0 "$ZLD" "$v" "$S/$f"
    no_traceback "$v on $f shows no traceback" "$ZLD" "$v" "$S/$f"
  done
done

echo
echo "--- 15. no network, no telemetry (static check of the shipped code)"
PKG_DIR="$(dirname "$(dirname "$(readlink -f "$ZLD")")")"
for d in "$ROOT/zlinuxdocs" "/usr/share/zlinuxdocs/zlinuxdocs"; do
  [ -d "$d" ] || continue
  if grep -rInE '\b(urllib|requests|http\.client|socket|urlopen|telemetry|analytics)\b' "$d" >/dev/null 2>&1; then
    fail "the program's own code makes no network calls" "$(grep -rlnE '\b(urllib|requests|socket)\b' "$d" | head -2 | tr '\n' ' ')"
  else
    pass "the program's own code makes no network calls ($d)"
  fi
  break
done
unset PKG_DIR

echo
echo "======================================================================"
if [ "$FAIL" -gt 0 ]; then
  echo "Failed tests:"
  for n in "${FAILED_NAMES[@]}"; do echo "  - $n"; done
  echo
fi
echo "TESTS: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1

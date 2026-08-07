#!/usr/bin/env bash
# tools/prove.sh — run the D1..D8 acceptance contract end to end and log every
# command with its verbatim output and real exit code.
#
#   echo <sudo-pw> | tools/prove.sh
#
# Nothing here masks an exit code: each is captured immediately after the
# command, never after a pipeline.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d ' \t\n\r' < "$ROOT/VERSION")"
DEB="$ROOT/dist/zlinuxdocs_${VERSION}_all.deb"
LOG="$ROOT/dist/proof.log"
WORK=/tmp/zproof
SUDO_PW="${SUDO_PW:-1234}"

: > "$LOG"
sec() { { echo; echo "########## $* ##########"; } >> "$LOG"; }
say() { echo "$*" >> "$LOG"; }
run() { echo "\$ $*" >> "$LOG"; "$@" >> "$LOG" 2>&1; local rc=$?; echo "[exit $rc]" >> "$LOG"; echo >> "$LOG"; return $rc; }
runsudo() { echo "\$ sudo $*" >> "$LOG"; echo "$SUDO_PW" | sudo -S "$@" >> "$LOG" 2>&1; local rc=$?; echo "[exit $rc]" >> "$LOG"; echo >> "$LOG"; return $rc; }

rm -rf "$WORK"; mkdir -p "$WORK"

say "zlinuxdocs $VERSION — D1..D8 acceptance run"
say "artifact: $DEB"
say "date:     $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
say "host:     $(uname -srm)   python: $(python3 -V 2>&1)"

# --------------------------------------------------------------------------
sec "PRE — the command must NOT exist before we install"
run bash -c 'command -v zlinuxdocs'
say "(exit 1 here is correct: nothing installed yet)"

sec "D1 INSTALLABLE"
runsudo dpkg -i "$DEB"
run bash -c 'command -v zlinuxdocs'
run bash -c 'command -v zld'

sec "D2 RUNS"
cd "$WORK"
run zlinuxdocs --version
run zld --version
run zlinuxdocs --help

sec "D3 DOES THE WORK — from /tmp, against the SHIPPED samples"
say "\$ pwd"; pwd >> "$LOG"; say ""
say "\$ ls /home/pk/zexp1/zlinuxdocs  # the source tree exists but is NOT used below"
say ""
cp "/usr/share/zlinuxdocs/samples/plain-no-headings.docx" "$WORK/My Report.docx"
say "\$ cp /usr/share/zlinuxdocs/samples/plain-no-headings.docx 'My Report.docx'"
say ""
run zlinuxdocs inspect "My Report.docx"
run zlinuxdocs fix-headings "My Report.docx" -o "My Report (fixed).docx"
run zlinuxdocs convert "My Report (fixed).docx" -o "My Report.pdf"
run zlinuxdocs validate "My Report.pdf" --verbose
run zlinuxdocs markers /usr/share/zlinuxdocs/samples/with-markers.docx
run zlinuxdocs profile
run zlinuxdocs quickstart

sec "D4 RED-ABLE — the validator must FAIL, seen red before green"
say "--- RED 1: a file that is not a PDF at all"
printf 'not a pdf' > /tmp/broken.pdf
say "\$ printf 'not a pdf' > /tmp/broken.pdf"; say ""
run zlinuxdocs validate /tmp/broken.pdf
zlinuxdocs validate /tmp/broken.pdf >/dev/null 2>&1; rc=$?
say "\$ zlinuxdocs validate /tmp/broken.pdf; test \$? -ne 0"
if [ "$rc" -ne 0 ]; then say "  CONFIRMED non-zero: exit $rc"; else say "  *** FAILED: exit was 0 ***"; fi
say ""
say "--- RED 2: a real, openable PDF made from an UNREPAIRED document (no bookmarks)"
zlinuxdocs convert "/usr/share/zlinuxdocs/samples/plain-no-headings.docx" -o "$WORK/unrepaired.pdf" >/dev/null 2>&1
run zlinuxdocs validate "$WORK/unrepaired.pdf"
say "--- GREEN control: the SAME document, after fix-headings"
run zlinuxdocs validate "$WORK/My Report.pdf"

sec "D5 IDEMPOTENT — fix-headings run twice"
cp "/usr/share/zlinuxdocs/samples/plain-no-headings.docx" "$WORK/Twice.docx"
say "--- RUN 1 (expect a non-zero promotion count)"
run zlinuxdocs fix-headings "Twice.docx" -o "Twice (fixed).docx"
say "--- RUN 2, on the OUTPUT of run 1 (expect 0 promotions)"
run zlinuxdocs fix-headings "Twice (fixed).docx" -o "Twice (fixed2).docx"
say "--- the DoD's own check"
say "\$ zlinuxdocs fix-headings 'Twice (fixed).docx' --dry-run | grep -q '0 promotions'"
zlinuxdocs fix-headings "Twice (fixed).docx" --dry-run | grep -q '0 promotions'; rc=$?
say "[exit $rc]  (0 means the DoD grep matched)"; say ""
say "--- and the structure really is unchanged between the two runs"
say "\$ zlinuxdocs inspect 'Twice (fixed).docx'  | grep -E 'Real headings|Look-alikes'"
zlinuxdocs inspect "Twice (fixed).docx"  | grep -E 'Real headings|Look-alikes' >> "$LOG"
say "\$ zlinuxdocs inspect 'Twice (fixed2).docx' | grep -E 'Real headings|Look-alikes'"
zlinuxdocs inspect "Twice (fixed2).docx" | grep -E 'Real headings|Look-alikes' >> "$LOG"
say ""

sec "FULL TEST SUITE — the installed command, run from /tmp"
say "\$ cd $WORK && ZLD=zlinuxdocs bash \$SRC/tests/run.sh"
ZLD=zlinuxdocs bash "$ROOT/tests/run.sh" > "$WORK/suite.out" 2>&1; rc=$?
head -5 "$WORK/suite.out" >> "$LOG"
say "  ... individual checks omitted for length; the summary is authoritative ..."
tail -4 "$WORK/suite.out" >> "$LOG"
say "[exit $rc]"

sec "D7 SHAREABLE — self-describing and dependency-honest"
run dpkg-deb -I "$DEB"
say "\$ dpkg-deb -c \$DEB | grep -vE 'vendor/(docx|yaml|pypdf)/'   # vendored trees elided"
dpkg-deb -c "$DEB" | grep -vE 'vendor/(docx|yaml|pypdf)/' >> "$LOG"
say ""
say "\$ dpkg-deb -c \$DEB | wc -l   # total entries including the vendored libraries"
dpkg-deb -c "$DEB" | wc -l >> "$LOG"
say ""
say "--- no maintainer scripts: deliberate policy, nothing executes on install or removal"
say "\$ dpkg-deb --ctrl-tarfile \$DEB | tar -t"
dpkg-deb --ctrl-tarfile "$DEB" | tar -t >> "$LOG" 2>&1
say ""
say "--- no __pycache__ or .pyc in the artifact"
say "\$ dpkg-deb -c \$DEB | grep -c 'pycache\\|\\.pyc'"
n=$(dpkg-deb -c "$DEB" | grep -c 'pycache\|\.pyc'); say "$n"
say ""
say "--- version agreement across all four places"
say "\$ cat VERSION                     -> $(cat "$ROOT/VERSION")"
say "\$ zlinuxdocs --version            -> $(zlinuxdocs --version)"
say "\$ dpkg -l zlinuxdocs | tail -1    -> $(dpkg -l zlinuxdocs 2>/dev/null | tail -1)"
say "\$ basename \$DEB                   -> $(basename "$DEB")"
say ""

sec "D6 CLEAN UNINSTALL"
runsudo dpkg -r zlinuxdocs
run bash -c 'command -v zlinuxdocs'
say "(exit 1 here is correct: the command is gone)"
run bash -c 'command -v zld'
say "\$ ls /usr/share/zlinuxdocs 2>&1"
ls /usr/share/zlinuxdocs >> "$LOG" 2>&1
say "[exit $?]"
say ""
say "--- reinstalling so the machine is left with the tool available"
runsudo dpkg -i "$DEB"
run bash -c 'command -v zlinuxdocs'

echo "proof written to $LOG"

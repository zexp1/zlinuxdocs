"""validate — check a PDF is fit to send, and fail loudly when it is not."""

import json

from zlinuxdocs.lib import pdfio, safety

HELP = "Check a PDF is fit to send. Exits with an error when it is not."

DESCRIPTION = """Checks the things that get a document handed back at the counter:

  * it really is a PDF, and it opens;
  * it is not password-protected;
  * it has pages;
  * it has bookmarks - the clickable chapter list;
  * its text can be selected and searched (not a photo of a page);
  * no leftover Word field codes such as MERGEFORMAT are showing;
  * its internal structure is sound (needs qpdf).

If any check fails the command exits with a non-zero status, so it can be used
in a script or a submission checklist."""

EXAMPLES = """Examples:
  zlinuxdocs validate "Final Report.pdf"
  zld check report.pdf
  zlinuxdocs validate report.pdf --json

  # Use it as a gate in a script
  if zlinuxdocs validate report.pdf; then echo "ready to send"; fi

  # A short leaflet has no chapters, so skip the bookmark check
  zlinuxdocs validate leaflet.pdf --no-bookmarks"""


def add_arguments(p):
    p.add_argument("file", nargs="?", help="the PDF file to check")
    p.add_argument("--no-bookmarks", action="store_true",
                   help="do not require a chapter list (for short one-piece documents)")
    p.add_argument("--no-text", action="store_true",
                   help="do not require selectable text (for scanned documents)")
    p.add_argument("--min-pages", type=int, default=1, help="require at least this many pages")
    p.add_argument("--json", action="store_true", help="print the result as JSON instead")
    p.add_argument("--verbose", "-v", action="store_true", help="list every check, including the ones that passed")
    p.add_argument("--examples", action="store_true", help="show example command lines and exit")


def run(args):
    if args.examples:
        print(EXAMPLES)
        return 0

    path = safety.require_input(args.file)
    result = pdfio.validate(
        path,
        want_bookmarks=not args.no_bookmarks,
        min_pages=args.min_pages,
        want_text=not args.no_text,
    )

    if args.json:
        print(json.dumps(
            {
                "file": result["file"],
                "ok": result["ok"],
                "pages": result["pages"],
                "bookmarks": result["bookmarks"],
                "size_kb": result["size_kb"],
                "checks": [{"check": c, "result": r, "detail": d} for c, r, d in result["checks"]],
                "problems": [p for p, _a in result["problems"]],
            },
            indent=2,
        ))
        return 0 if result["ok"] else 1

    print("Checking: %s" % result["file"])
    print("Pages: %d    Bookmarks: %d    Size: %d KB"
          % (result["pages"], result["bookmarks"], result["size_kb"]))
    print("")

    for name, state, detail in result["checks"]:
        if state == "pass" and not args.verbose:
            continue
        mark = {"pass": "OK  ", "fail": "FAIL", "skip": "SKIP"}[state]
        print("  [%s] %s%s" % (mark, name, ("  - " + detail) if detail else ""))
    print("")

    for note in result["notes"]:
        print(note)
    if result["notes"]:
        print("")

    if result["ok"]:
        print("RESULT: PASS - this PDF is fit to send.")
        return 0

    print("RESULT: FAIL - %d problem(s) found.\n" % len(result["problems"]))
    for i, (problem, advice) in enumerate(result["problems"], 1):
        print("%d. %s" % (i, problem))
        for line in advice.splitlines():
            print("   %s" % line)
        print("")
    return 1

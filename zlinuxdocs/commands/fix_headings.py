"""fix-headings — turn text that only LOOKS like a heading into a real one."""

from zlinuxdocs.lib import docxio, safety

HELP = "Turn text that only looks like a heading into a real heading."

DESCRIPTION = """Some documents are typed with headings that are only big and bold. They read
like headings, but the computer does not know they are headings — so the PDF
you make from them has no chapter list to click through.

This command finds those lines ("1 - Introduction", "2.1 Scope", "CHAPTER IV")
and marks them as genuine headings, so bookmarks appear in the PDF.

It never changes your original file unless you ask for --in-place, and it never
overwrites an existing file unless you add --force. Running it twice is safe:
the second run finds nothing to do and reports 0 promotions."""

EXAMPLES = """Examples:
  # See what would change, without touching anything
  zlinuxdocs fix-headings "Final Report v2 (1).docx" --dry-run

  # Write a repaired copy (the original is left alone)
  zlinuxdocs fix-headings "Final Report v2 (1).docx" -o "Final Report fixed.docx"

  # Replace the original, keeping a .bak copy beside it
  zld fix report.docx --in-place

  # Try it on the example that ships with the program
  zlinuxdocs fix-headings /usr/share/zlinuxdocs/samples/plain-no-headings.docx -o /tmp/fixed.docx"""


def add_arguments(p):
    p.add_argument("file", nargs="?", help="the Word .docx file to repair")
    p.add_argument("-o", "--output", help="where to write the repaired copy")
    p.add_argument("--dry-run", action="store_true",
                   help="show what would change and write nothing")
    p.add_argument("--in-place", action="store_true",
                   help="replace the original file (a .bak copy is kept beside it)")
    p.add_argument("--force", action="store_true",
                   help="allow an existing output file to be replaced")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="list every line that would change")
    p.add_argument("--examples", action="store_true", help="show example command lines and exit")


def run(args):
    if args.examples:
        print(EXAMPLES)
        return 0

    path = safety.require_input(args.file, kinds=[".docx"])
    out = safety.resolve_output(
        path, args.output, args.in_place, args.force,
        default_ext=".docx", dry_run=args.dry_run,
    )

    doc = docxio.open_document(path)
    plan = docxio.plan_promotions(doc)
    n = plan["promotions"]

    print("Looked at %d paragraphs in '%s'." % (plan["paragraph_count"], path))

    if n == 0:
        print("Nothing to change - 0 promotions. The headings here are already real.")
    else:
        verb = "Would promote" if args.dry_run else "Promoted"
        print("%s %d line(s) to real headings - %d promotions." % (verb, n, n))
        for style in ("Heading 1", "Heading 2", "Heading 3"):
            c = plan["counts"][style]
            if c:
                print("    %-20s %d" % (docxio.PLAIN_LEVEL_NAME[style] + "s:", c))
        if plan["title_rows"]:
            print("    %-20s %d" % ("title page lines:", len(plan["title_rows"])))

    if args.verbose and plan["rows"]:
        print("")
        print("The lines concerned:")
        for _p, style, text, reason in plan["rows"]:
            print("    %-20s %s" % (docxio.PLAIN_LEVEL_NAME[style] + ":", _clip(text)))
            print("    %-20s (matched %s)" % ("", reason))

    if args.dry_run:
        print("")
        print("Nothing was written (--dry-run).")
        if n:
            print("To save the repaired copy, run the same command again like this:")
            print("    zlinuxdocs fix-headings \"%s\" -o \"fixed.docx\"" % path)
        return 0

    bak = None
    if args.in_place:
        bak = safety.backup(path)

    docxio.apply_promotions(doc, plan)
    docxio.save_document(doc, out)

    print("")
    if bak:
        print("Saved over the original. Your previous version is kept at:")
        print("    %s" % bak)
    else:
        print("Saved: %s" % out)
    print("")
    print("What to do next:")
    print("    zlinuxdocs convert \"%s\" -o report.pdf" % out)
    print("    zlinuxdocs validate report.pdf")
    return 0


def _clip(text, n=64):
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"

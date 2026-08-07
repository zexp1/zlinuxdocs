"""inspect — say what is really inside a Word document."""

import os

from zlinuxdocs.lib import docxio, safety

HELP = "Show what is really inside a Word document (headings, tables, markers)."

EXAMPLES = """Examples:
  zlinuxdocs inspect "Final Report v2 (1).docx"
  zlinuxdocs info /usr/share/zlinuxdocs/samples/plain-no-headings.docx
  zld show report.docx --verbose"""


def add_arguments(p):
    p.add_argument("file", nargs="?", help="the Word .docx file to look at")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="also list every heading and every style in use")
    p.add_argument("--examples", action="store_true", help="show example command lines and exit")


def run(args):
    if args.examples:
        print(EXAMPLES)
        return 0

    path = safety.require_input(args.file, kinds=[".docx"])
    doc = docxio.open_document(path)

    paragraphs = list(doc.paragraphs)
    real_headings = []
    pseudo = []
    style_use = {}
    words = 0

    for p in paragraphs:
        name = docxio.style_name_of(p)
        text = p.text or ""
        words += len(text.split())
        if text.strip():
            style_use[name or "(no style)"] = style_use.get(name or "(no style)", 0) + 1
        if name.startswith("Heading"):
            real_headings.append((name, text.strip()))
        else:
            target, _reason = docxio.classify(text)
            if target:
                pseudo.append((target, text.strip()))

    tables = len(doc.tables)
    table_cells_text = 0
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                words += len(cell.text.split())
                table_cells_text += 1
    sections = len(doc.sections)
    markers = docxio.scan_markers(path)

    size_kb = os.path.getsize(path) // 1024

    print("File:            %s" % path)
    print("Size:            %d KB" % size_kb)
    print("Paragraphs:      %d" % len(paragraphs))
    print("Words (approx):  %d" % words)
    print("Tables:          %d%s" % (tables, "  (%d cells)" % table_cells_text if tables else ""))
    print("Page setups:     %d" % sections)
    print("Real headings:   %d   <- these become clickable bookmarks in a PDF" % len(real_headings))
    print("Look-alikes:     %d   <- text that reads like a heading but is not one" % len(pseudo))
    print("[V] markers:     %d" % len(markers))
    print("")

    if pseudo:
        print("This document has %d line(s) that LOOK like headings but are plain text." % len(pseudo))
        print("A PDF made from it will have %s."
              % ("no chapter bookmarks at all" if not real_headings else "an incomplete chapter list"))
        print("")
        print("What to do:")
        print("    zlinuxdocs fix-headings \"%s\" -o fixed.docx" % path)
        print("    zlinuxdocs convert fixed.docx -o report.pdf")
        print("")
        show = pseudo if args.verbose else pseudo[:5]
        print("The first few look-alikes:" if not args.verbose else "All look-alikes:")
        for target, text in show:
            print("    %-18s %s" % (docxio.PLAIN_LEVEL_NAME.get(target, target) + ":", _clip(text)))
        if not args.verbose and len(pseudo) > 5:
            print("    ... and %d more (run again with --verbose to see them all)" % (len(pseudo) - 5))
        print("")
    elif real_headings:
        print("Good news: every heading in this document is a real heading.")
        print("A PDF made from it will have a working chapter list.")
        print("")
        print("What to do next:")
        print("    zlinuxdocs convert \"%s\" -o report.pdf" % path)
        print("    zlinuxdocs validate report.pdf")
        print("")
    else:
        print("This document has no headings of any kind — it reads as one long block.")
        print("That is fine for a letter or a form; a long report usually wants headings.")
        print("")

    if args.verbose:
        if real_headings:
            print("Headings already in place:")
            for name, text in real_headings:
                indent = "  " * (int(name[-1]) - 1 if name[-1].isdigit() else 0)
                print("    %s%-11s %s" % (indent, name, _clip(text)))
            print("")
        print("Styles in use:")
        for name, n in sorted(style_use.items(), key=lambda kv: (-kv[1], kv[0])):
            print("    %-28s %d paragraph(s)" % (name, n))
        print("")
        if markers:
            print("[V] markers found — run 'zlinuxdocs markers' for the full list.")
            print("")

    return 0


def _clip(text, n=68):
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"

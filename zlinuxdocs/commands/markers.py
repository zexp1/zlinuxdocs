"""markers — find the [V] verification marks somebody left in a document."""

from zlinuxdocs.lib import docxio, safety

HELP = "Find the [V] verification marks left in a document."

DESCRIPTION = """Reviewers often type a marker such as [V] next to a figure or a claim that
still needs to be checked. This command lists every one of them, in paragraphs
AND inside tables, so nothing goes out unverified.

It only reads. It never changes your document - clearing a marker is your
decision, not the program's."""

EXAMPLES = """Examples:
  zlinuxdocs markers "Final Report v2 (1).docx"
  zld todo report.docx
  zlinuxdocs markers report.docx --tsv -o markers.tsv
  zlinuxdocs markers report.docx --marker "[TODO]"
  zlinuxdocs flags /usr/share/zlinuxdocs/samples/with-markers.docx"""


def add_arguments(p):
    p.add_argument("file", nargs="?", help="the Word .docx file to scan")
    p.add_argument("--marker", default=docxio.MARKER,
                   help="the marker text to look for (default: [V])")
    p.add_argument("--tsv", action="store_true",
                   help="print as tab-separated columns for a spreadsheet")
    p.add_argument("-o", "--output", help="write the list to a file instead of the screen")
    p.add_argument("--force", action="store_true", help="allow an existing output file to be replaced")
    p.add_argument("--examples", action="store_true", help="show example command lines and exit")


def run(args):
    if args.examples:
        print(EXAMPLES)
        return 0

    path = safety.require_input(args.file, kinds=[".docx"])
    rows = docxio.scan_markers(path, args.marker)

    if args.tsv:
        lines = ["section\twhere\ttext"]
        lines += ["%s\t%s\t%s" % (r["section"], r["where"], r["text"]) for r in rows]
        body = "\n".join(lines) + "\n"
    else:
        if not rows:
            body = ("No %s markers found in '%s'.\nNothing is waiting to be verified.\n"
                    % (args.marker, path))
        else:
            out = ["Found %d %s marker(s) in '%s'.\n" % (len(rows), args.marker, path)]
            last = None
            for i, r in enumerate(rows, 1):
                if r["section"] != last:
                    out.append("Under: %s" % r["section"])
                    last = r["section"]
                out.append("  %2d. (%s) %s" % (i, r["where"], r["text"]))
            out.append("")
            out.append("These are notes somebody left for a checker. Deal with each one in")
            out.append("Word or LibreOffice, then remove the marker text by hand.")
            body = "\n".join(out) + "\n"

    if args.output:
        out_path = safety.resolve_output(path, args.output, False, args.force, default_ext=".tsv")
        safety.prepare_parent(out_path)
        safety.guard_write(out_path)
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(body)
        print("Wrote %d marker(s) to %s" % (len(rows), out_path))
    else:
        print(body, end="")

    return 0

"""convert — turn a document into a PDF (or another office format)."""

import os
import shutil
import subprocess
import tempfile

from zlinuxdocs.lib import deps, profile as profile_lib, safety
from zlinuxdocs.lib.errors import UserError

HELP = "Turn a document into a PDF with a working chapter list."

DESCRIPTION = """Makes a PDF from a Word document, using LibreOffice, with bookmarks (the
clickable chapter list) and a searchable text layer switched on.

It can also go the other way: give -o a name ending in .docx and an old .doc
file becomes a modern .docx.

ABOUT PDF/A: --pdfa asks LibreOffice to export in a PDF/A archival flavour.
It does NOT prove the result conforms. Nothing in this program can verify
PDF/A conformance - that needs a dedicated validator such as veraPDF. So do
not tell anyone the output "is PDF/A" on this program's word. It is a request,
not a certificate."""

EXAMPLES = """Examples:
  # The normal case
  zlinuxdocs convert "Final Report v2 (1).docx" -o "Final Report.pdf"

  # Short form
  zld pdf report.docx -o report.pdf

  # Replace a PDF you made earlier
  zlinuxdocs convert report.docx -o report.pdf --force

  # Modernise an old .doc file
  zlinuxdocs convert "Old Memo.doc" -o "Old Memo.docx"

  # Check first, without converting
  zlinuxdocs convert report.docx -o report.pdf --dry-run"""

INPUT_KINDS = [".docx", ".doc", ".odt", ".rtf", ".txt", ".html", ".htm", ".fodt"]

_FILTERS = {
    ".docx": "docx:MS Word 2007 XML",
    ".odt": "odt:writer8",
    ".txt": "txt:Text (encoded):UTF8",
    ".html": "html:HTML (StarWriter)",
}


def add_arguments(p):
    p.add_argument("file", nargs="?", help="the document to convert")
    p.add_argument("-o", "--output", help="the file to create (usually ending in .pdf)")
    p.add_argument("--force", action="store_true",
                   help="allow an existing output file to be replaced")
    p.add_argument("--dry-run", action="store_true",
                   help="say what would happen and convert nothing")
    p.add_argument("--profile", help="name of the print profile to use (default: release)")
    p.add_argument("--profile-file", help="use your own profile file instead of the shipped one")
    p.add_argument("--pdfa", action="store_true",
                   help="ask for a PDF/A archival flavour (REQUESTED, NOT VERIFIED - "
                        "conformance is not claimed; see the description above)")
    p.add_argument("--timeout", type=int, default=300,
                   help="give up after this many seconds (default: 300)")
    p.add_argument("--verbose", "-v", action="store_true", help="show the LibreOffice command used")
    p.add_argument("--examples", action="store_true", help="show example command lines and exit")


def run(args):
    if args.examples:
        print(EXAMPLES)
        return 0

    path = safety.require_input(args.file, kinds=INPUT_KINDS)
    out = safety.resolve_output(path, args.output, False, args.force,
                                default_ext=".pdf", dry_run=args.dry_run)
    if out is None:
        out = os.path.splitext(os.path.basename(path))[0] + ".pdf"

    out_ext = os.path.splitext(out)[1].lower()
    if out_ext not in [".pdf"] + list(_FILTERS):
        raise UserError(
            "this program does not know how to make a '%s' file." % (out_ext or "(no extension)"),
            "What to do: end the output name with one of these:\n"
            "    .pdf   .docx   .odt   .txt   .html\n"
            "For example:\n"
            "    zlinuxdocs convert \"%s\" -o output.pdf" % path,
        )

    data = profile_lib.load(args.profile_file)
    resolved = profile_lib.resolve(data, args.profile)

    if out_ext == ".pdf":
        conv = profile_lib.soffice_pdf_filter(resolved, pdfa=args.pdfa)
        what = "PDF"
    else:
        conv = _FILTERS[out_ext]
        what = out_ext.lstrip(".").upper()

    if args.dry_run:
        print("Would convert:  %s" % path)
        print("Would create:   %s" % out)
        print("Format:         %s" % what)
        print("Using:          LibreOffice (soffice), print profile '%s'" % resolved.get("_name"))
        if args.pdfa:
            print("PDF/A:          requested, NOT verified - conformance is not claimed")
        if os.path.exists(out):
            print("Note:           '%s' already exists; add --force to replace it." % out)
        print("")
        print("Nothing was written (--dry-run).")
        return 0

    deps.require("soffice")
    safety.prepare_parent(out)
    safety.guard_write(out)

    print("Converting '%s' ..." % path)
    print("(this can take up to a minute for a long document)")

    tmp_out = tempfile.mkdtemp(prefix="zlinuxdocs-out-")
    tmp_profile = tempfile.mkdtemp(prefix="zlinuxdocs-lo-")
    try:
        cmd = [
            "soffice", "--headless", "--norestore", "--nolockcheck", "--nodefault",
            "-env:UserInstallation=file://%s" % tmp_profile,
            "--convert-to", conv, "--outdir", tmp_out, os.path.abspath(path),
        ]
        if args.verbose:
            print("Command: %s" % " ".join(cmd))
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
        except subprocess.TimeoutExpired:
            raise UserError(
                "LibreOffice did not finish within %d seconds." % args.timeout,
                "What to do: try again with a longer limit —\n"
                "    zlinuxdocs convert \"%s\" -o \"%s\" --timeout 900\n"
                "If it still hangs, close any open LibreOffice window and retry."
                % (path, out),
            )

        produced = os.path.join(
            tmp_out, os.path.splitext(os.path.basename(path))[0] + out_ext
        )
        if not os.path.isfile(produced):
            detail = (proc.stderr or proc.stdout or "").strip().splitlines()
            first = detail[0][:160] if detail else "LibreOffice produced no output file"
            raise UserError(
                "the conversion did not produce a %s (%s)." % (what, first),
                "What to do:\n"
                "  - check the document opens normally in LibreOffice;\n"
                "  - close any open LibreOffice window and try again;\n"
                "  - if the input is an old .doc, convert it to .docx first:\n"
                "        zlinuxdocs convert \"%s\" -o converted.docx" % path,
            )
        shutil.move(produced, out)
    finally:
        shutil.rmtree(tmp_out, ignore_errors=True)
        shutil.rmtree(tmp_profile, ignore_errors=True)

    size_kb = os.path.getsize(out) // 1024
    print("")
    print("Created: %s (%d KB)" % (out, size_kb))
    if args.pdfa:
        print("")
        print("PDF/A was REQUESTED but NOT verified. This program cannot prove")
        print("conformance, so please do not describe the file as certified PDF/A.")
    if out_ext == ".pdf":
        print("")
        print("What to do next - check the PDF is fit to send:")
        print("    zlinuxdocs validate \"%s\"" % out)
    return 0

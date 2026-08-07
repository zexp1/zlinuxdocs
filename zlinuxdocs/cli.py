"""The command line: verbs, aliases, help and plain-language errors.

Nothing here touches the network. Nothing here reports anything anywhere.
"""

import argparse
import difflib
import os
import sys

from zlinuxdocs.__version__ import __version__
from zlinuxdocs.commands import (
    convert as convert_cmd,
    fix_headings as fix_headings_cmd,
    inspect_cmd,
    markers as markers_cmd,
    profile_cmd,
    validate_cmd,
)
from zlinuxdocs.lib import paths
from zlinuxdocs.lib.errors import UserError, emit

PROG = "zlinuxdocs"

ONE_LINER = (
    "zlinuxdocs - look inside Word documents, repair their headings, "
    "turn them into good PDFs, and check those PDFs before you send them."
)

# canonical verb -> (module, aliases, one-line purpose)
VERBS = [
    ("inspect", inspect_cmd, ["info", "show"],
     "Say what is really inside a Word document."),
    ("fix-headings", fix_headings_cmd, ["fix", "repair"],
     "Turn text that only looks like a heading into a real heading."),
    ("convert", convert_cmd, ["pdf", "to-pdf"],
     "Turn a document into a PDF with a working chapter list."),
    ("validate", validate_cmd, ["check", "verify"],
     "Check a PDF is fit to send (exits with an error if not)."),
    ("markers", markers_cmd, ["flags", "todo"],
     "Find the [V] verification marks left in a document."),
    ("profile", profile_cmd, ["settings"],
     "Show or export the house print settings."),
]

HELPERS = [
    ("quickstart", ["start", "tutorial"], "A five-command walkthrough using the shipped examples."),
    ("examples", ["howto"], "Real command lines you can copy and paste."),
    ("samples", ["demo"], "List the example documents that came with the program."),
    ("help", [], "Show help, or help for one command: zlinuxdocs help convert"),
]

ALIAS_TO_VERB = {}
for _name, _mod, _aliases, _purpose in VERBS:
    ALIAS_TO_VERB[_name] = _name
    for _a in _aliases:
        ALIAS_TO_VERB[_a] = _name
for _name, _aliases, _purpose in HELPERS:
    ALIAS_TO_VERB[_name] = _name
    for _a in _aliases:
        ALIAS_TO_VERB[_a] = _name

MODULES = {name: mod for name, mod, _a, _p in VERBS}
ALIASES_OF = {name: aliases for name, _m, aliases, _p in VERBS}
ALIASES_OF.update({name: aliases for name, aliases, _p in HELPERS})


# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------
def orientation():
    lines = [ONE_LINER, ""]
    lines.append("Commands:")
    for name, _mod, aliases, purpose in VERBS:
        lines.append("  %-13s %s" % (name, purpose))
        if aliases:
            lines.append("  %-13s   also written as: %s" % ("", ", ".join(aliases)))
    lines.append("")
    lines.append("Getting started:")
    for name, aliases, purpose in HELPERS:
        lines.append("  %-13s %s" % (name, purpose))
    lines.append("")
    lines.append("The short name 'zld' does exactly the same as 'zlinuxdocs'.")
    lines.append("")
    lines.append("New here?   Run:  zlinuxdocs quickstart")
    lines.append("Full help:  Run:  zlinuxdocs --help   (or: zlinuxdocs help convert)")
    return "\n".join(lines)


def epilog():
    rows = []
    for name, _mod, aliases, _purpose in VERBS:
        rows.append("  %-13s %s" % (name, ", ".join(aliases) if aliases else "-"))
    return (
        "Every command also answers to a shorter name:\n\n"
        "  COMMAND       ALSO WRITTEN AS\n" + "\n".join(rows) + "\n\n"
        "The program itself answers to 'zld' as well as 'zlinuxdocs'.\n\n"
        "New here?  zlinuxdocs quickstart\n"
        "Examples:  zlinuxdocs examples          (or --examples on any command)\n"
        "Help on one command:  zlinuxdocs help convert\n\n"
        "This program works entirely offline. It makes no network connections and\n"
        "collects no information about you or your documents.\n"
    )


def quickstart_text():
    sd = paths.samples_dir() or "/usr/share/zlinuxdocs/samples"
    return """zlinuxdocs quickstart
=====================

You do not need a document of your own - example ones came with the program.
Copy and paste these five commands, one at a time.

  1. Work somewhere harmless, and take a copy of an example document.

     cd /tmp
     cp "{sd}/plain-no-headings.docx" "My Report.docx"

  2. Look at what is inside it.

     zlinuxdocs inspect "My Report.docx"

     It will tell you the document has lines that LOOK like headings but are
     really plain text. That is why PDFs made from it have no chapter list.

  3. Repair it. Your original is left untouched; a new file is written.

     zlinuxdocs fix-headings "My Report.docx" -o "My Report (fixed).docx"

  4. Make the PDF.

     zlinuxdocs convert "My Report (fixed).docx" -o "My Report.pdf"

  5. Check the PDF before you send it to anybody.

     zlinuxdocs validate "My Report.pdf"

     PASS means it has pages, a clickable chapter list, searchable text and no
     leftover Word field codes. FAIL tells you exactly what to fix.

That is the whole tool. Two more commands are there when you need them:

     zlinuxdocs markers "My Report.docx"    # find [V] notes left by a reviewer
     zlinuxdocs profile                     # see the page and PDF settings

Tips
----
  * Put file names in quotes if they contain spaces or brackets:
        zlinuxdocs inspect "Final Report v2 (1).docx"
  * Add --dry-run to any command that writes, to see what it would do first.
  * Type 'zld' instead of 'zlinuxdocs' if you prefer - they are the same.
  * Every command explains itself:  zlinuxdocs help convert
""".format(sd=sd)


def examples_text():
    sd = paths.samples_dir() or "/usr/share/zlinuxdocs/samples"
    return """zlinuxdocs examples
===================

Looking inside a document
    zlinuxdocs inspect "Final Report v2 (1).docx"
    zlinuxdocs info report.docx --verbose
    zld show "{sd}/mixed-tables.docx"

Repairing headings
    zlinuxdocs fix-headings "Final Report v2 (1).docx" --dry-run
    zlinuxdocs fix-headings "Final Report v2 (1).docx" -o "Final Report fixed.docx"
    zlinuxdocs fix report.docx -o fixed.docx --force
    zld repair report.docx --in-place          # keeps a .bak of the original

Making a PDF
    zlinuxdocs convert "Final Report fixed.docx" -o "Final Report.pdf"
    zld pdf report.docx -o report.pdf --force
    zlinuxdocs convert "Old Memo.doc" -o "Old Memo.docx"    # modernise an old file
    zlinuxdocs convert report.docx -o report.pdf --dry-run

Checking a PDF
    zlinuxdocs validate "Final Report.pdf"
    zld check report.pdf --verbose
    zlinuxdocs verify leaflet.pdf --no-bookmarks      # a one-page leaflet
    zlinuxdocs validate report.pdf --json

Verification marks left by a reviewer
    zlinuxdocs markers "{sd}/with-markers.docx"
    zld todo report.docx --tsv -o markers.tsv
    zlinuxdocs flags report.docx --marker "[TODO]"

Print settings
    zlinuxdocs profile
    zlinuxdocs settings --list
    zlinuxdocs profile -o my-profile.yaml
    zlinuxdocs convert report.docx -o report.pdf --profile-file my-profile.yaml

The whole job, end to end
    cd /tmp
    cp "{sd}/plain-no-headings.docx" "My Report.docx"
    zlinuxdocs inspect      "My Report.docx"
    zlinuxdocs fix-headings "My Report.docx" -o "My Report (fixed).docx"
    zlinuxdocs convert      "My Report (fixed).docx" -o "My Report.pdf"
    zlinuxdocs validate     "My Report.pdf"
""".format(sd=sd)


def samples_text():
    d = paths.samples_dir()
    if not d or not os.path.isdir(d):
        return ("The example documents are not installed.\n"
                "Reinstall the package:  sudo dpkg -i zlinuxdocs_<version>_all.deb\n")
    out = ["Example documents that came with this program, in:", "  %s" % d, ""]
    readme = os.path.join(d, "README.md")
    described = {}
    if os.path.isfile(readme):
        with open(readme, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("| `"):
                    parts = [c.strip() for c in line.strip().strip("|").split("|")]
                    if len(parts) >= 2:
                        described[parts[0].strip("`")] = parts[1]
    for f in sorted(os.listdir(d)):
        if not f.endswith(".docx"):
            continue
        out.append("  %-28s %s" % (f, described.get(f, "")))
    out.append("")
    out.append("Try one:")
    out.append("    zlinuxdocs inspect \"%s\"" % os.path.join(d, "plain-no-headings.docx"))
    out.append("")
    out.append("Full walkthrough:  zlinuxdocs quickstart")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
class PlainParser(argparse.ArgumentParser):
    """argparse that speaks plainly and never dumps a wall of text on error."""

    def error(self, message):
        sys.stderr.write("%s: %s\n" % (self.prog, message))
        sys.stderr.write("\nWhat to do: see how this command is used —\n")
        sys.stderr.write("    %s --help\n" % self.prog)
        sys.exit(2)


def build_parser():
    parser = PlainParser(
        prog=PROG,
        description=ONE_LINER,
        epilog=epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )
    parser.add_argument("--version", action="version", version="%s %s" % (PROG, __version__))
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    for name, mod, aliases, purpose in VERBS:
        desc = getattr(mod, "DESCRIPTION", purpose)
        p = sub.add_parser(
            name,
            aliases=aliases,
            help=purpose,
            description=desc,
            epilog=getattr(mod, "EXAMPLES", ""),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        mod.add_arguments(p)
        p.set_defaults(_module=mod)

    for name, aliases, purpose in HELPERS:
        p = sub.add_parser(name, aliases=aliases, help=purpose,
                           formatter_class=argparse.RawDescriptionHelpFormatter)
        if name == "help":
            p.add_argument("topic", nargs="?", help="the command you want help with")
        p.set_defaults(_module=None, _helper=name)

    return parser


def suggest(word):
    known = sorted(ALIAS_TO_VERB.keys())
    close = difflib.get_close_matches(word, known, n=2, cutoff=0.55)
    return close


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv:
        print(orientation())
        return 0

    first = argv[0]

    if first in ("-h", "--help"):
        build_parser().print_help()
        return 0
    if first == "--version":
        print("%s %s" % (PROG, __version__))
        return 0

    if not first.startswith("-") and first not in ALIAS_TO_VERB:
        close = suggest(first)
        sys.stderr.write("%s: there is no command called '%s'.\n" % (PROG, first))
        if close:
            sys.stderr.write("\n  Did you mean '%s'?\n" % close[0])
            if len(close) > 1:
                sys.stderr.write("  Or perhaps '%s'?\n" % close[1])
            sys.stderr.write("\n      %s %s %s\n"
                             % (PROG, close[0], " ".join(argv[1:]) or "<your-file>"))
        sys.stderr.write("\n  The commands are: %s\n"
                         % ", ".join(n for n, _m, _a, _p in VERBS))
        sys.stderr.write("  For a walkthrough run:  %s quickstart\n" % PROG)
        return 2

    # `help <verb>` -> `<verb> --help`
    if ALIAS_TO_VERB.get(first) == "help":
        if len(argv) > 1:
            topic = ALIAS_TO_VERB.get(argv[1])
            if topic is None:
                close = suggest(argv[1])
                sys.stderr.write("%s: there is no command called '%s'.\n" % (PROG, argv[1]))
                if close:
                    sys.stderr.write("\n  Did you mean '%s'?\n" % close[0])
                return 2
            if topic in MODULES:
                argv = [topic, "--help"]
            else:
                argv = [topic]
        else:
            build_parser().print_help()
            return 0

    parser = build_parser()
    args = parser.parse_args(argv)

    helper = getattr(args, "_helper", None)
    if helper == "quickstart":
        print(quickstart_text(), end="")
        return 0
    if helper == "examples":
        print(examples_text(), end="")
        return 0
    if helper == "samples":
        print(samples_text(), end="")
        return 0
    if helper == "help":
        parser.print_help()
        return 0

    module = getattr(args, "_module", None)
    if module is None:
        print(orientation())
        return 0

    try:
        return module.run(args)
    except UserError as err:
        return emit(err)
    except KeyboardInterrupt:
        sys.stderr.write("\n%s: stopped at your request. Nothing was left half-written.\n" % PROG)
        return 130
    except BrokenPipeError:
        return 0
    except Exception as exc:  # never show a traceback to a user
        sys.stderr.write(
            "%s: something went wrong that this program did not expect.\n\n"
            "  Details (for a report): %s: %s\n\n"
            "  What to do: check the file opens normally in Word or LibreOffice.\n"
            "  If it does, please report this at\n"
            "      https://github.com/zexp1/zlinuxdocs/issues\n"
            % (PROG, type(exc).__name__, str(exc)[:200])
        )
        if os.environ.get("ZLINUXDOCS_DEBUG"):
            import traceback
            traceback.print_exc()
        return 70

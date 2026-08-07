"""Plain-language errors. A stack trace reaching the user is a defect."""

import sys

PROG = "zlinuxdocs"


class UserError(Exception):
    """An error we can explain in one or two plain sentences.

    ``advice`` is what the user should DO next. Always fill it in.
    """

    def __init__(self, message, advice=None, exit_code=1):
        super().__init__(message)
        self.message = message
        self.advice = advice
        self.exit_code = exit_code


def emit(err):
    """Print a UserError the way a non-technical reader can act on it."""
    sys.stderr.write("%s: %s\n" % (PROG, err.message))
    if err.advice:
        sys.stderr.write("\n")
        for line in err.advice.rstrip().splitlines():
            sys.stderr.write("  %s\n" % line if line.strip() else "\n")
    return err.exit_code


def missing_file(path):
    return UserError(
        "there is no file called '%s'." % path,
        "What to do: check the spelling, or list the folder to see the real name:\n"
        "    ls -la\n"
        "If the name has spaces, put it in quotes:\n"
        "    zlinuxdocs inspect \"Final Report v2 (1).docx\"",
    )


def not_a_docx(path, detail=""):
    extra = (" (%s)" % detail) if detail else ""
    return UserError(
        "'%s' is not a readable Word .docx file%s." % (path, extra),
        "What to do:\n"
        "  - If it is an old .doc file, turn it into .docx first:\n"
        "        zlinuxdocs convert \"%s\" -o converted.docx\n"
        "  - If it came from an email, download it again — the copy may be truncated.\n"
        "  - If it is a PDF, use 'zlinuxdocs validate' instead." % path,
    )

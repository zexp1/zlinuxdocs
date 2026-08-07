"""Write-safety. This program edits other people's documents; it must never
destroy one by accident.

Rules (sealed by the R4 rulings):
  * nothing is written over the input unless --in-place is given explicitly;
  * an existing output file is never overwritten without --force;
  * --dry-run is available everywhere a write happens.
"""

import os
import shutil

from zlinuxdocs.lib.errors import UserError, missing_file


def require_input(path, kinds=None):
    """Check an input file exists and (optionally) has an accepted extension."""
    if not path:
        raise UserError(
            "no file was given.",
            "What to do: name the file after the command, for example:\n"
            "    zlinuxdocs inspect \"My Report.docx\"\n"
            "Try the shipped examples first:  zlinuxdocs quickstart",
        )
    if not os.path.exists(path):
        raise missing_file(path)
    if os.path.isdir(path):
        raise UserError(
            "'%s' is a folder, not a file." % path,
            "What to do: name one document, for example:\n"
            "    zlinuxdocs inspect \"%s/My Report.docx\"" % path.rstrip("/"),
        )
    if not os.access(path, os.R_OK):
        raise UserError(
            "'%s' cannot be read (permission denied)." % path,
            "What to do: copy it somewhere you own, then try again:\n"
            "    cp \"%s\" ~/ && cd ~" % path,
        )
    if kinds:
        ext = os.path.splitext(path)[1].lower()
        if ext not in kinds:
            raise UserError(
                "'%s' is a %s file, and this command works on %s files."
                % (path, ext or "(no extension)", " or ".join(kinds)),
                "What to do: check you named the right file.\n"
                "If it is an old .doc file, turn it into .docx first:\n"
                "    zlinuxdocs convert \"%s\" -o converted.docx" % path,
            )
    return path


def resolve_output(inp, out, in_place, force, default_ext=None, dry_run=False):
    """Work out where to write, refusing anything unsafe.

    Returns the output path, or None when nothing should be written.
    """
    if in_place and out:
        raise UserError(
            "you asked for both --in-place and -o, and they mean opposite things.",
            "What to do: pick one.\n"
            "  Write a NEW file (recommended):   -o \"fixed.docx\"\n"
            "  Overwrite the original in place:  --in-place",
        )

    if in_place:
        return inp

    if not out:
        if dry_run:
            return None
        guess = "fixed" + (default_ext or os.path.splitext(inp)[1] or ".out")
        raise UserError(
            "no output file was given, and this command will not overwrite your original.",
            "What to do: say where the new file should go with -o, for example:\n"
            "    zlinuxdocs <command> \"%s\" -o \"%s\"\n"
            "Or preview without writing anything:\n"
            "    zlinuxdocs <command> \"%s\" --dry-run" % (inp, guess, inp),
        )

    if os.path.abspath(out) == os.path.abspath(inp):
        raise UserError(
            "the output file is the same as the input file.",
            "What to do: choose a different name for -o, or pass --in-place if you\n"
            "really do want the original replaced (a .bak copy is kept).",
        )

    if os.path.exists(out) and not force and not dry_run:
        raise UserError(
            "'%s' already exists, and it will not be overwritten." % out,
            "What to do: either choose another name,\n"
            "    -o \"%s\"\n"
            "or repeat the command with --force to replace the existing file."
            % _suggest_alt(out),
        )
    return out


def _suggest_alt(path):
    base, ext = os.path.splitext(path)
    return "%s-2%s" % (base, ext)


def prepare_parent(path):
    """Create the parent folder if needed, with a plain message on failure."""
    parent = os.path.dirname(os.path.abspath(path))
    if os.path.isdir(parent):
        return
    try:
        os.makedirs(parent, exist_ok=True)
    except OSError as exc:
        raise UserError(
            "the folder '%s' could not be created (%s)." % (parent, exc.strerror or exc),
            "What to do: choose an output path inside a folder you can write to,\n"
            "for example your home folder:\n"
            "    -o ~/fixed.docx",
        )


def backup(path):
    """Keep a .bak beside an in-place edit. Returns the backup path."""
    bak = path + ".bak"
    n = 1
    while os.path.exists(bak):
        n += 1
        bak = "%s.bak%d" % (path, n)
    shutil.copy2(path, bak)
    return bak


def guard_write(path):
    """Raise a plain error if `path` cannot be written."""
    parent = os.path.dirname(os.path.abspath(path)) or "."
    if not os.access(parent, os.W_OK):
        raise UserError(
            "nothing can be written into '%s' (permission denied)." % parent,
            "What to do: write to your home folder instead, for example:\n"
            "    -o ~/%s" % os.path.basename(path),
        )

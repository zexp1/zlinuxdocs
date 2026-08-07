"""PDF checks.

Adapted from twdpt1 tools/dprkit/validate_pdf.py, which gated 16 government
volumes. The point of this module is that it can go RED: a PDF that would
embarrass you at a submission counter makes the command exit non-zero.
"""

import os
import re
import subprocess

from zlinuxdocs.lib.errors import UserError
from zlinuxdocs.lib import deps

FIELD_CODE_PATTERNS = [
    ("MERGEFORMAT", r"MERGEFORMAT"),
    ("{ PAGE }", r"\{\s*PAGE\s*\}"),
    ("{ REF ... }", r"\{\s*REF\s"),
    ("{ TOC ... }", r"\{\s*TOC\s"),
    ("Error! Reference source not found", r"Error!\s*Reference source not found"),
    ("Error! Bookmark not defined", r"Error!\s*Bookmark not defined"),
]

MIN_TEXT_CHARS = 40


def _run(cmd, timeout=60):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timed out"
    except FileNotFoundError:
        return -127, "", "not installed"
    except Exception as exc:
        return -1, "", str(exc)


def page_count(path):
    deps.require("pdfinfo")
    code, out, _err = _run(["pdfinfo", path])
    if code != 0:
        return 0
    m = re.search(r"^Pages:\s*(\d+)", out, re.M)
    return int(m.group(1)) if m else 0


def is_encrypted(path):
    code, out, _err = _run(["pdfinfo", path])
    if code != 0:
        return False
    return bool(re.search(r"^Encrypted:\s*yes", out, re.M | re.I))


def extract_text(path):
    deps.require("pdftotext")
    code, out, _err = _run(["pdftotext", path, "-"], timeout=120)
    return out if code == 0 else ""


def bookmark_count(path):
    """Count every entry in the PDF outline (bookmark) tree, at any depth."""
    deps.require_pypdf()
    from pypdf import PdfReader

    try:
        reader = PdfReader(path)
        outline = reader.outline
    except Exception:
        return 0
    if not outline:
        return 0

    def count(items):
        n = 0
        for item in items:
            if isinstance(item, list):
                n += count(item)
            else:
                n += 1
        return n

    try:
        return count(outline)
    except Exception:
        return 0


def qpdf_check(path):
    """Return (ran, ok, message). ran=False when qpdf is not installed."""
    if not deps.have("qpdf"):
        return False, True, deps.soft_warn("qpdf")
    code, out, err = _run(["qpdf", "--check", path], timeout=120)
    blob = (out or "") + (err or "")
    if code == 0:
        return True, True, None
    # qpdf exits 3 for warnings on files that still open fine.
    if code == 3 and "error" not in blob.lower():
        return True, True, "Note: qpdf reported warnings (the file still opens)."
    first = next((ln.strip() for ln in blob.splitlines() if ln.strip()), "qpdf reported a problem")
    return True, False, first[:200]


def looks_like_pdf(path):
    try:
        with open(path, "rb") as fh:
            return fh.read(5) == b"%PDF-"
    except OSError as exc:
        raise UserError(
            "'%s' could not be read (%s)." % (path, exc.strerror or exc),
            "What to do: check the file is really there —\n    ls -la \"%s\"" % path,
        )


def validate(path, want_bookmarks=True, min_pages=1, want_text=True):
    """Run every check. Returns a result dict; `ok` False means exit non-zero."""
    result = {
        "file": path,
        "ok": True,
        "pages": 0,
        "bookmarks": 0,
        "size_kb": 0,
        "problems": [],   # plain-language, each with a "what to do"
        "notes": [],
        "checks": [],     # (name, "pass"/"fail"/"skip", detail)
    }

    def fail(name, detail, advice):
        result["ok"] = False
        result["checks"].append((name, "fail", detail))
        result["problems"].append((detail, advice))

    def ok(name, detail=""):
        result["checks"].append((name, "pass", detail))

    def skip(name, detail=""):
        result["checks"].append((name, "skip", detail))

    if not os.path.exists(path):
        from zlinuxdocs.lib.errors import missing_file
        raise missing_file(path)

    result["size_kb"] = os.path.getsize(path) // 1024

    if os.path.getsize(path) == 0:
        fail("readable PDF", "the file is empty (0 bytes)",
             "Produce it again — the last export did not finish.")
        return result

    if not looks_like_pdf(path):
        fail("readable PDF", "this is not a PDF file at all",
             "Real PDF files begin with the characters %%PDF. This one does not, so it\n"
             "is some other kind of file that has been given a .pdf name.\n"
             "Check what it really is:\n"
             "    file \"%s\"" % path)
        return result
    ok("readable PDF")

    if is_encrypted(path):
        fail("not password-protected", "the PDF is password-protected, so it cannot be checked",
             "Open it in a PDF reader, enter the password, and save an unprotected copy.")
        return result
    ok("not password-protected")

    pages = page_count(path)
    result["pages"] = pages
    if pages < min_pages:
        fail("has pages", "the PDF has no readable pages",
             "The file is damaged. Produce the PDF again:\n"
             "    zlinuxdocs convert \"your-document.docx\" -o \"%s\" --force" % path)
        return result
    ok("has pages", "%d pages" % pages)

    bookmarks = bookmark_count(path)
    result["bookmarks"] = bookmarks
    if want_bookmarks and bookmarks == 0:
        fail("has bookmarks",
             "the PDF has no bookmarks, so nobody can jump to a chapter",
             "This happens when the Word document's headings only LOOK like headings.\n"
             "Fix the document first, then convert again:\n"
             "    zlinuxdocs fix-headings \"your-document.docx\" -o fixed.docx\n"
             "    zlinuxdocs convert fixed.docx -o \"%s\" --force" % path)
    elif not want_bookmarks:
        skip("has bookmarks", "not required (--no-bookmarks)")
    else:
        ok("has bookmarks", "%d bookmarks" % bookmarks)

    text = extract_text(path)
    stripped = text.strip()
    if want_text and len(stripped) < MIN_TEXT_CHARS:
        fail("text can be selected and searched",
             "the PDF has almost no selectable text (%d characters)" % len(stripped),
             "It is probably a scan or an image-only export. Convert from the original\n"
             "Word file instead of scanning it:\n"
             "    zlinuxdocs convert \"your-document.docx\" -o \"%s\" --force" % path)
    elif not want_text:
        skip("text can be selected and searched", "not required (--no-text)")
    else:
        ok("text can be selected and searched", "%d characters" % len(stripped))

    leaked = [label for label, pat in FIELD_CODE_PATTERNS if re.search(pat, text, re.I)]
    if leaked:
        fail("no broken field codes",
             "the text contains leftover Word field codes: %s" % ", ".join(leaked),
             "Open the document in Word or LibreOffice, press Ctrl+A then F9 to refresh\n"
             "the fields, save, and convert again.")
    else:
        ok("no broken field codes")

    ran, good, message = qpdf_check(path)
    if not ran:
        skip("deep structure check", "qpdf is not installed")
        if message:
            result["notes"].append(message)
    elif good:
        ok("deep structure check")
        if message:
            result["notes"].append(message)
    else:
        fail("deep structure check", "the PDF's internal structure is damaged (%s)" % message,
             "Produce the PDF again:\n"
             "    zlinuxdocs convert \"your-document.docx\" -o \"%s\" --force" % path)

    return result

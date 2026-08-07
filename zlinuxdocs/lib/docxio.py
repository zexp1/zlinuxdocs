"""Reading and repairing .docx structure.

Adapted from twdpt1 tools/dprkit/restyle_docx.py and vmarkers.py, which were
proven on 16 real government volumes (57-150 pages, 40-128 bookmarks each).

The important part — and the reason PDF bookmarks appear at all — is that a
heading style must carry an OUTLINE LEVEL. A paragraph that merely looks big
and bold produces no bookmark. That is what `fix-headings` repairs.
"""

import re
import zipfile
import xml.etree.ElementTree as ET

from zlinuxdocs.lib.errors import UserError, not_a_docx

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def q(tag):
    return "{%s}%s" % (W, tag)


# --------------------------------------------------------------------------
# Pseudo-heading detection
# --------------------------------------------------------------------------
# Ordered deepest-first so "1.1.1 Scope" is never mistaken for a level-2
# heading. Each entry: (compiled pattern, style name, plain description).
_PATTERNS = [
    (re.compile(r"^\s*\d+\.\d+\.\d+(?:\.\d+)?[\s ]+\S.*$"), "Heading 3", "sub-section number like '1.2.3'"),
    (re.compile(r"^\s*\d+\.\d+[\s ]+\S.*$"), "Heading 2", "section number like '1.2'"),
    (re.compile(r"^\s*(?:\d+|[IVXLCDM]+)\s*[—–-]\s+\S.*$"), "Heading 1", "chapter line like '1 - Title'"),
    (re.compile(r"^\s*(?:CHAPTER|ANNEXURE|APPENDIX|SECTION|PART)\s+(?:\d+|[IVXLCDM]+)\b.*$", re.I),
     "Heading 1", "the word CHAPTER/ANNEXURE/APPENDIX and a number"),
]

_MAX_HEADING_CHARS = 200  # a 400-character paragraph is prose, not a heading

_OUTLINE_FOR = {"Heading 1": 0, "Heading 2": 1, "Heading 3": 2}

PLAIN_LEVEL_NAME = {
    "Heading 1": "chapter heading",
    "Heading 2": "section heading",
    "Heading 3": "sub-section heading",
}


def classify(text):
    """Return (style_name, plain_reason) for a paragraph, or (None, None)."""
    if not text or not text.strip():
        return None, None
    if len(text) > _MAX_HEADING_CHARS:
        return None, None
    if "\n" in text:
        return None, None
    for pattern, style, reason in _PATTERNS:
        if pattern.match(text):
            return style, reason
    return None, None


# --------------------------------------------------------------------------
# Opening documents
# --------------------------------------------------------------------------
def open_document(path):
    """Open a .docx with python-docx, translating every failure to plain words."""
    from zlinuxdocs.lib.deps import require_python_docx

    docx = require_python_docx()
    if not zipfile.is_zipfile(path):
        raise not_a_docx(path, "the file is not in Word's .docx format")
    try:
        return docx.Document(path)
    except zipfile.BadZipFile:
        raise not_a_docx(path, "the file is damaged or incomplete")
    except KeyError:
        raise not_a_docx(path, "the file is missing its main document part")
    except Exception as exc:  # last resort: never show a traceback
        raise not_a_docx(path, str(exc)[:120])


def read_document_xml(path):
    """Return the parsed word/document.xml. Uses only the Python standard
    library, so `markers` works even if nothing else is installed."""
    if not zipfile.is_zipfile(path):
        raise not_a_docx(path, "the file is not in Word's .docx format")
    try:
        with zipfile.ZipFile(path) as z:
            return ET.fromstring(z.read("word/document.xml"))
    except KeyError:
        raise not_a_docx(path, "the file is missing its main document part")
    except zipfile.BadZipFile:
        raise not_a_docx(path, "the file is damaged or incomplete")
    except ET.ParseError as exc:
        raise not_a_docx(path, "the internal XML is corrupt (%s)" % exc)


def element_text(el):
    parts = []
    for child in el.iter():
        if child.tag in (q("t"), q("delText")):
            parts.append(child.text or "")
        elif child.tag in (q("br"), q("tab")):
            parts.append(" ")
    return "".join(parts)


# --------------------------------------------------------------------------
# Style plumbing
# --------------------------------------------------------------------------
def _set_outline_level(style, level):
    """Give a paragraph style an outline level.

    Without this, LibreOffice and Word both export a PDF with no bookmark tree,
    which is the single most common complaint about converted documents.
    Returns True if the level was set.
    """
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    try:
        elem = style._element
        pPr = elem.find(qn("w:pPr"))
        if pPr is None:
            pPr = OxmlElement("w:pPr")
            elem.append(pPr)
        lvl = pPr.find(qn("w:outlineLvl"))
        if lvl is None:
            lvl = OxmlElement("w:outlineLvl")
            pPr.append(lvl)
        lvl.set(qn("w:val"), str(level))
        return True
    except Exception:
        return False


def ensure_style(doc, name, outline_level=None):
    """Find or create a paragraph style, and stamp its outline level."""
    from docx.enum.style import WD_STYLE_TYPE

    found = None
    for s in doc.styles:
        try:
            if s.name == name:
                found = s
                break
        except Exception:
            continue
    if found is None:
        try:
            found = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        except Exception as exc:
            raise UserError(
                "the heading style '%s' could not be created in this document (%s)." % (name, exc),
                "What to do: open the document in Word or LibreOffice, save it again\n"
                "as .docx, and re-run the command.",
            )
    if outline_level is not None:
        _set_outline_level(found, outline_level)
    return found


def style_name_of(paragraph):
    try:
        return paragraph.style.name if paragraph.style is not None else ""
    except Exception:
        return ""


# --------------------------------------------------------------------------
# The repair itself
# --------------------------------------------------------------------------
def plan_promotions(doc):
    """Work out what would change, without changing anything.

    Returns a dict with the counts and a list of (style, text, reason) rows.
    Running this on an already-repaired document yields zero promotions — that
    is the idempotency guarantee, and tests/run.sh proves it.
    """
    paragraphs = list(doc.paragraphs)
    rows = []
    counts = {"Heading 1": 0, "Heading 2": 0, "Heading 3": 0}
    title_rows = []

    first_heading_idx = None
    for idx, p in enumerate(paragraphs):
        style, _reason = classify(p.text)
        if style:
            first_heading_idx = idx
            break

    if first_heading_idx is not None:
        for p in paragraphs[:first_heading_idx]:
            if not p.text.strip():
                continue
            target = "Title" if not title_rows else "Subtitle"
            if style_name_of(p) != target:
                title_rows.append((p, target))

    for p in paragraphs:
        style, reason = classify(p.text)
        if not style:
            continue
        if style_name_of(p) == style:
            continue  # already a real heading: nothing to do
        rows.append((p, style, p.text.strip(), reason))
        counts[style] += 1

    return {
        "paragraph_count": len(paragraphs),
        "counts": counts,
        "rows": rows,
        "title_rows": title_rows,
        "promotions": sum(counts.values()),
    }


def apply_promotions(doc, plan):
    """Apply a plan produced by plan_promotions()."""
    for name, level in _OUTLINE_FOR.items():
        ensure_style(doc, name, outline_level=level)
    if plan["title_rows"]:
        ensure_style(doc, "Title")
        ensure_style(doc, "Subtitle")

    for p, target in plan["title_rows"]:
        try:
            p.style = target
        except Exception:
            pass
    for p, style, _text, _reason in plan["rows"]:
        p.style = style
    return plan["promotions"]


def save_document(doc, path):
    from zlinuxdocs.lib.safety import prepare_parent, guard_write

    prepare_parent(path)
    guard_write(path)
    try:
        doc.save(path)
    except OSError as exc:
        raise UserError(
            "the file '%s' could not be written (%s)." % (path, exc.strerror or exc),
            "What to do: check there is free space (run 'df -h .') and that you are\n"
            "allowed to write in that folder. Writing to your home folder always works:\n"
            "    -o ~/fixed.docx",
        )


# --------------------------------------------------------------------------
# [V] verification markers
# --------------------------------------------------------------------------
MARKER = "[V]"


def scan_markers(path, marker=MARKER):
    """Find verification markers in paragraphs AND table cells.

    Standard library only — no dependency on python-docx or lxml.
    """
    root = read_document_xml(path)
    body = root.find("w:body", NS)
    if body is None:
        raise not_a_docx(path, "the document body is missing")

    results = []
    current_heading = ""

    def record(text, where):
        results.append(
            {
                "section": current_heading or "(before the first heading)",
                "where": where,
                "text": " ".join(text.split())[:200],
            }
        )

    def walk(container, where):
        nonlocal current_heading
        for child in container:
            if child.tag == q("p"):
                text = element_text(child)
                ppr = child.find(q("pPr"))
                is_heading = False
                if ppr is not None:
                    if ppr.find(q("outlineLvl")) is not None:
                        is_heading = True
                    pstyle = ppr.find(q("pStyle"))
                    if pstyle is not None:
                        val = pstyle.get(q("val")) or ""
                        if val.lower().startswith("heading") or val.lower() == "title":
                            is_heading = True
                if is_heading and text.strip():
                    current_heading = " ".join(text.split())[:80]
                if marker in text:
                    record(text, where)
            elif child.tag == q("tbl"):
                for r_i, row in enumerate(child.findall("w:tr", NS), 1):
                    for c_i, cell in enumerate(row.findall("w:tc", NS), 1):
                        cell_text = element_text(cell)
                        if marker in cell_text:
                            record(cell_text, "table row %d, column %d" % (r_i, c_i))

    walk(body, "paragraph")
    return results


def count_markers(path, marker=MARKER):
    try:
        return len(scan_markers(path, marker))
    except UserError:
        return None

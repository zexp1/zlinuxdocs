"""Dependency checks. Every absent dependency gets one plain sentence that
names the apt package to install. Never a traceback."""

import shutil

from zlinuxdocs.lib.errors import UserError

# tool -> (apt package, what it is used for)
_TOOLS = {
    "soffice": ("libreoffice-writer", "turning documents into PDF"),
    "pdfinfo": ("poppler-utils", "counting the pages of a PDF"),
    "pdftotext": ("poppler-utils", "reading the text inside a PDF"),
    "qpdf": ("qpdf", "the deep structural check of a PDF"),
}


def have(tool):
    return shutil.which(tool) is not None


def require(tool):
    """Raise a plain-language UserError if `tool` is not installed."""
    if have(tool):
        return shutil.which(tool)
    pkg, purpose = _TOOLS.get(tool, (tool, "this step"))
    raise UserError(
        "'%s' is not installed on this computer, and it is needed for %s." % (tool, purpose),
        "What to do — install it with one command:\n"
        "    sudo apt install %s\n"
        "\n"
        "Then run the same zlinuxdocs command again.\n"
        "(The 'inspect', 'fix-headings' and 'markers' commands do not need it.)" % pkg,
    )


def soft_warn(tool):
    """Return a one-line warning string for an optional tool, or None."""
    if have(tool):
        return None
    pkg, purpose = _TOOLS.get(tool, (tool, "an optional check"))
    return (
        "Note: '%s' is not installed, so %s was skipped.\n"
        "      To enable it:  sudo apt install %s" % (tool, purpose, pkg)
    )


def require_python_docx():
    """Import python-docx, explaining clearly if the vendored copy cannot load."""
    try:
        import docx  # noqa: F401
        return docx
    except ImportError as exc:
        detail = str(exc)
        if "lxml" in detail:
            raise UserError(
                "a required system library (python3-lxml) is missing.",
                "What to do — install it with one command:\n"
                "    sudo apt install python3-lxml\n"
                "\n"
                "Then run the same zlinuxdocs command again.",
            )
        raise UserError(
            "the document-reading library that ships with this program did not load (%s)." % detail,
            "What to do: reinstall the package —\n"
            "    sudo dpkg -i zlinuxdocs_<version>_all.deb",
        )


def require_pypdf():
    try:
        from pypdf import PdfReader  # noqa: F401
        import pypdf
        return pypdf
    except ImportError as exc:
        raise UserError(
            "the PDF-reading library that ships with this program did not load (%s)." % exc,
            "What to do: reinstall the package —\n"
            "    sudo dpkg -i zlinuxdocs_<version>_all.deb",
        )


def require_yaml():
    try:
        import yaml  # noqa: F401
        return yaml
    except ImportError as exc:
        raise UserError(
            "the settings-file library that ships with this program did not load (%s)." % exc,
            "What to do: reinstall the package —\n"
            "    sudo dpkg -i zlinuxdocs_<version>_all.deb",
        )

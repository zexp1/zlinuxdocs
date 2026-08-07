"""The house print profile — the page setup, typography and PDF settings that
were used for a real 16-volume government submission.

A profile is plain YAML. `zlinuxdocs profile` shows it; `convert` reads the
`pdf:` section from it to build the LibreOffice export options.
"""

import copy
import os

from zlinuxdocs.lib import deps, paths
from zlinuxdocs.lib.errors import UserError

DEFAULT_PROFILE_FILE = "house_profile.yaml"


def profile_path(name=None):
    d = paths.require_profiles_dir()
    fname = name if (name and name.endswith((".yaml", ".yml"))) else DEFAULT_PROFILE_FILE
    p = os.path.join(d, fname)
    if not os.path.isfile(p):
        raise UserError(
            "there is no profile file called '%s'." % fname,
            "What to do: list the ones that ship with the program:\n"
            "    zlinuxdocs profile --list",
        )
    return p


def load(path=None):
    yaml = deps.require_yaml()
    p = path or profile_path()
    try:
        with open(p, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except OSError as exc:
        raise UserError(
            "the settings file '%s' could not be read (%s)." % (p, exc.strerror or exc),
            "What to do: reinstall the package, or point at your own file with --file.",
        )
    except Exception as exc:
        raise UserError(
            "the settings file '%s' is not valid YAML (%s)." % (p, str(exc).splitlines()[0]),
            "What to do: fix the indentation, or use the shipped profile instead by\n"
            "leaving out --file.",
        )
    if not isinstance(data, dict):
        raise UserError(
            "the settings file '%s' does not contain a settings block." % p,
            "What to do: use the shipped profile instead by leaving out --file.",
        )
    return data


def named_profiles(data):
    return sorted((data.get("profiles") or {}).keys())


def resolve(data, name=None):
    """Merge a named profile over the base settings."""
    name = name or data.get("profile") or "release"
    profiles = data.get("profiles") or {}
    if name not in profiles:
        raise UserError(
            "there is no profile called '%s' in this settings file." % name,
            "What to do: pick one of these —\n    %s\n"
            "or list them with:\n    zlinuxdocs profile --list"
            % ", ".join(named_profiles(data) or ["(none defined)"]),
        )
    merged = copy.deepcopy({k: v for k, v in data.items() if k != "profiles"})
    merged = _deep_merge(merged, copy.deepcopy(profiles[name]))
    merged["_name"] = name
    return merged


def _deep_merge(base, over):
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def summarise(resolved):
    """A short, plain-language description of what the profile does."""
    doc = resolved.get("document") or {}
    page = doc.get("page") or {}
    typ = doc.get("type") or {}
    pdf = resolved.get("pdf") or {}
    margins = page.get("margins") or {}
    lines = [
        "Profile:      %s" % resolved.get("_name", "?"),
        "Paper:        %s %s, margins %s, binding gutter %s"
        % (
            str(page.get("size", "?")).upper(),
            page.get("orientation", "?"),
            margins.get("top", "?"),
            page.get("gutter", "none"),
        ),
        "Body text:    %s %s, line spacing %s%s"
        % (
            typ.get("bodyFont", "?"),
            typ.get("bodySize", "?"),
            typ.get("lineHeight", "?"),
            ", justified" if typ.get("justify") else "",
        ),
        "Headings:     %s" % typ.get("headingFont", "?"),
        "Contents:     %s"
        % ("depth %s with dot leaders" % ((doc.get("toc") or {}).get("levels", "?"))
           if (doc.get("toc") or {}).get("enabled") else "not generated"),
        "PDF:          bookmarks %s, tagged %s, fonts embedded %s"
        % (
            "on" if pdf.get("exportBookmarks", True) else "off",
            "on" if pdf.get("taggedPdf", True) else "off",
            "on" if ((pdf.get("fonts") or {}).get("embed", True)) else "off",
        ),
        "PDF/A:        %s" % _pdfa_line(pdf),
    ]
    return "\n".join(lines)


def _pdfa_line(pdf):
    std = str(pdf.get("standard", "none")).lower()
    if std in ("", "none", "null"):
        return "not requested (see 'zlinuxdocs convert --help' for why we do not claim it)"
    return "%s REQUESTED, NOT VERIFIED — conformance is not claimed" % std


def soffice_pdf_filter(resolved, pdfa=False):
    """Build the LibreOffice pdf export filter string from the profile."""
    pdf = (resolved or {}).get("pdf") or {}
    images = pdf.get("images") or {}

    version = 0
    if pdfa:
        std = str(pdf.get("standard", "pdfa-2b")).lower()
        version = 1 if "1" in std else (3 if "3" in std else 2)

    opts = {
        "UseTaggedPDF": ("boolean", "true" if pdf.get("taggedPdf", True) else "false"),
        "ExportBookmarks": ("boolean", "true" if pdf.get("exportBookmarks", True) else "false"),
        "ExportNotes": ("boolean", "true" if pdf.get("exportNotes", False) else "false"),
        "ExportNotesInMargin": ("boolean", "false"),
        "ExportPlaceholders": ("boolean", "true" if pdf.get("exportPlaceholders", False) else "false"),
        "ExportHiddenSlides": ("boolean", "false"),
        "EmbedStandardFonts": ("boolean", "true" if ((pdf.get("fonts") or {}).get("embedStandardFonts", True)) else "false"),
        "ReduceImageResolution": ("boolean", "true" if images.get("downsample", False) else "false"),
        "MaxImageResolution": ("long", str(images.get("dpi", 300))),
        "Quality": ("long", str(images.get("jpegQuality", 90))),
        "UseLosslessCompression": ("boolean", "true" if str(images.get("compression", "lossless")) == "lossless" else "false"),
        "OpenBookmarkLevels": ("long", "-1"),
        "SelectPdfVersion": ("long", str(version)),
    }
    body = ",".join(
        '"%s":{"type":"%s","value":"%s"}' % (k, t, v) for k, (t, v) in sorted(opts.items())
    )
    return "pdf:writer_pdf_Export:{%s}" % body

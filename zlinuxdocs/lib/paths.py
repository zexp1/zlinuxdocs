"""Where the shipped samples, profiles and docs live."""

import os

from zlinuxdocs.lib.errors import UserError


def install_root():
    """Root that holds zlinuxdocs/, vendor/, samples/, profiles/.

    Set by the entry script (bin/zlinuxdocs). Falls back to walking up from
    this file so the package is importable in a test harness too.
    """
    root = os.environ.get("ZLINUXDOCS_ROOT")
    if root and os.path.isdir(root):
        return root
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return here


def _first_existing(*candidates):
    for c in candidates:
        if c and os.path.isdir(c):
            return c
    return None


def samples_dir():
    root = install_root()
    return _first_existing(
        os.path.join(root, "samples"),            # installed layout
        os.path.join(root, "share", "samples"),   # source tree
        "/usr/share/zlinuxdocs/samples",
    )


def profiles_dir():
    root = install_root()
    return _first_existing(
        os.path.join(root, "profiles"),
        os.path.join(root, "share", "profiles"),
        "/usr/share/zlinuxdocs/profiles",
    )


def require_samples_dir():
    d = samples_dir()
    if not d:
        raise UserError(
            "the example documents that ship with this program are missing.",
            "What to do: reinstall the package —\n"
            "    sudo dpkg -i zlinuxdocs_<version>_all.deb",
        )
    return d


def require_profiles_dir():
    d = profiles_dir()
    if not d:
        raise UserError(
            "the print-profile files that ship with this program are missing.",
            "What to do: reinstall the package —\n"
            "    sudo dpkg -i zlinuxdocs_<version>_all.deb",
        )
    return d

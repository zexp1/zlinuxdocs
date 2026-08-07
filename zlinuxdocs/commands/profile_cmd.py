"""profile — show or export the house print settings."""

import os
import shutil

from zlinuxdocs.lib import paths, profile as profile_lib, safety

HELP = "Show or export the house print settings (paper, fonts, PDF options)."

DESCRIPTION = """The print profile is a plain settings file describing the page size, margins,
fonts, table of contents and PDF options used for a real government submission
of 16 volumes. The 'convert' command reads its PDF section.

This command lets you look at it, and copy it out so you can adjust it and
pass it back with 'convert --profile-file mine.yaml'."""

EXAMPLES = """Examples:
  zlinuxdocs profile                     # a plain-language summary
  zlinuxdocs settings --list             # which profiles exist
  zlinuxdocs profile --show draft        # the draft profile in full
  zlinuxdocs profile --raw               # the whole settings file
  zlinuxdocs profile -o my-profile.yaml  # copy it out to adjust
  zlinuxdocs convert report.docx -o report.pdf --profile-file my-profile.yaml"""


def add_arguments(p):
    p.add_argument("name", nargs="?", help="which profile to describe (default: release)")
    p.add_argument("--list", action="store_true", help="list the profiles that are available")
    p.add_argument("--show", help="describe a named profile")
    p.add_argument("--raw", action="store_true", help="print the whole settings file as-is")
    p.add_argument("--file", dest="profile_file", help="read your own settings file instead")
    p.add_argument("--path", action="store_true", help="print where the settings file lives")
    p.add_argument("-o", "--output", help="copy the settings file to this path so you can edit it")
    p.add_argument("--force", action="store_true", help="allow an existing output file to be replaced")
    p.add_argument("--examples", action="store_true", help="show example command lines and exit")


def run(args):
    if args.examples:
        print(EXAMPLES)
        return 0

    src = args.profile_file or profile_lib.profile_path()

    if args.path:
        print(src)
        return 0

    if args.output:
        out = safety.resolve_output(src, args.output, False, args.force, default_ext=".yaml")
        safety.prepare_parent(out)
        safety.guard_write(out)
        shutil.copyfile(src, out)
        print("Copied the print settings to: %s" % out)
        print("")
        print("Edit it, then use it like this:")
        print("    zlinuxdocs convert report.docx -o report.pdf --profile-file \"%s\"" % out)
        return 0

    data = profile_lib.load(args.profile_file)

    if args.raw:
        with open(src, "r", encoding="utf-8") as fh:
            print(fh.read(), end="")
        return 0

    names = profile_lib.named_profiles(data)

    if args.list:
        print("Print profiles available in %s:" % os.path.basename(src))
        print("")
        for n in names:
            desc = ((data.get("profiles") or {}).get(n) or {}).get("description", "")
            print("  %-10s %s" % (n, desc))
        print("")
        print("Use one like this:")
        print("    zlinuxdocs convert report.docx -o report.pdf --profile %s" % (names[0] if names else "release"))
        return 0

    wanted = args.show or args.name
    resolved = profile_lib.resolve(data, wanted)

    print("Print settings from: %s" % src)
    print("")
    print(profile_lib.summarise(resolved))
    print("")
    print("Other profiles here: %s" % ", ".join(n for n in names if n != resolved.get("_name")))
    print("")
    print("To see the file itself:      zlinuxdocs profile --raw")
    print("To copy it out and edit it:  zlinuxdocs profile -o my-profile.yaml")
    if paths.samples_dir():
        print("To try it:                   zlinuxdocs convert %s -o /tmp/sample.pdf"
              % os.path.join(paths.samples_dir(), "proper-headings.docx"))
    return 0

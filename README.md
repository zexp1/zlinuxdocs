# zlinuxdocs

**You were emailed a Word document. You need a PDF that will not be handed back
at the counter.** That is what this does.

It looks inside `.docx` files, repairs headings that only *look* like headings,
turns documents into PDFs with a working clickable chapter list, and checks
those PDFs before you send them — failing loudly when something is wrong.

Works entirely offline. No network connections, no telemetry, no account.

```
zlinuxdocs inspect      "Final Report v2 (1).docx"
zlinuxdocs fix-headings "Final Report v2 (1).docx" -o "Final Report fixed.docx"
zlinuxdocs convert      "Final Report fixed.docx"  -o "Final Report.pdf"
zlinuxdocs validate     "Final Report.pdf"
```

The short name `zld` does exactly the same thing, if you would rather not type
ten characters.

---

## First 5 minutes

You do **not** need a document of your own — example ones are installed with
the program. Copy and paste these, one at a time.

```bash
# 1. Work somewhere harmless, and take a copy of an example document.
cd /tmp
cp "/usr/share/zlinuxdocs/samples/plain-no-headings.docx" "My Report.docx"

# 2. Look at what is inside it.
zlinuxdocs inspect "My Report.docx"
```

It will tell you the document has 12 lines that *look* like headings
("1 - Introduction", "1.1 Scope") but are really just bold text. That is why
PDFs made from such documents have no chapter list.

```bash
# 3. Repair it. Your original is left untouched; a new file is written.
zlinuxdocs fix-headings "My Report.docx" -o "My Report (fixed).docx"

# 4. Make the PDF.
zlinuxdocs convert "My Report (fixed).docx" -o "My Report.pdf"

# 5. Check the PDF before you send it to anybody.
zlinuxdocs validate "My Report.pdf"
```

`RESULT: PASS` means the PDF has pages, a clickable chapter list, searchable
text and no leftover Word field codes. `RESULT: FAIL` tells you exactly what to
fix, in plain words, and exits with an error so a script can catch it.

Anything unclear? The program explains itself:

```bash
zlinuxdocs quickstart      # this walkthrough, from the program itself
zlinuxdocs examples        # real command lines you can copy
zlinuxdocs samples         # what the example documents demonstrate
zlinuxdocs help convert    # help for one command
```

**Tip:** put file names in quotes whenever they contain spaces or brackets —
`zlinuxdocs inspect "Final Report v2 (1).docx"`. Add `--dry-run` to any command
that writes, to see what it would do before it does it.

---

## Install

```bash
sudo dpkg -i zlinuxdocs_0.1.0_all.deb

# If dpkg complains about a missing dependency, this pulls it in:
sudo apt-get install -f
```

Then, optionally, for the `convert` command and the deepest PDF check:

```bash
sudo apt install libreoffice-writer qpdf
```

Check it worked:

```bash
zlinuxdocs --version
zld quickstart
```

Uninstall:

```bash
sudo dpkg -r zlinuxdocs
```

The package installs no scripts. Nothing runs on install or on removal — it is
a plain drop of files into `/usr/bin/` and `/usr/share/zlinuxdocs/`.

`Architecture: all` means the same `.deb` works on any processor (amd64, arm64,
Raspberry Pi); the code is pure Python.

**Supported:** Debian 12+, Ubuntu 22.04+, Linux Mint, Pop!\_OS, and the same
under WSL. Other distributions are not packaged; the tarball layout is plain
enough to unpack by hand if you are determined.

---

## The six commands

| command | also written as | what it does |
|---|---|---|
| `inspect` | `info`, `show` | Says what is really inside a Word document. Read-only. |
| `fix-headings` | `fix`, `repair` | Turns look-alike headings into real ones. Idempotent. |
| `convert` | `pdf`, `to-pdf` | Makes a PDF with a working chapter list. |
| `validate` | `check`, `verify` | Checks a PDF is fit to send. Exits non-zero when it is not. |
| `markers` | `flags`, `todo` | Lists the `[V]` marks a reviewer left behind. Read-only. |
| `profile` | `settings` | Shows or exports the house print settings. |

Plus four helpers: `quickstart` (`start`, `tutorial`), `examples` (`howto`),
`samples` (`demo`), and `help`.

And the program itself answers to both `zlinuxdocs` and `zld`.

Get a command wrong and it guesses what you meant:

```
$ zlinuxdocs covert report.docx
zlinuxdocs: there is no command called 'covert'.

  Did you mean 'convert'?

      zlinuxdocs convert report.docx
```

### `inspect` — what is really in there

```bash
zlinuxdocs inspect "Final Report v2 (1).docx"
zlinuxdocs info report.docx --verbose        # every heading, every style
zld show "/usr/share/zlinuxdocs/samples/mixed-tables.docx"
```

Reports paragraphs, words, tables, page setups, real headings, look-alike
headings and `[V]` markers — then tells you what to do about it.

### `fix-headings` — the repair

```bash
zlinuxdocs fix-headings "Final Report v2 (1).docx" --dry-run           # preview
zlinuxdocs fix-headings "Final Report v2 (1).docx" -o "fixed.docx"     # normal
zlinuxdocs fix report.docx -o fixed.docx --force                       # replace output
zld repair report.docx --in-place                                      # keeps a .bak
```

Finds lines like `1 - Introduction`, `2.1 Scope`, `1.2.3 Method` and
`ANNEXURE III`, and marks them as genuine headings **with an outline level** —
which is the technical detail that makes bookmarks appear in the PDF.

It does not fall for text that merely mentions a number: `See 1.1 above for the
scope note` stays a paragraph, and so does any line longer than a heading
plausibly is.

**Idempotent.** Run it twice and the second run reports `0 promotions`. That is
tested, not intended.

### `convert` — make the PDF

```bash
zlinuxdocs convert "Final Report fixed.docx" -o "Final Report.pdf"
zld pdf report.docx -o report.pdf --force
zlinuxdocs convert report.docx -o report.pdf --dry-run
zlinuxdocs convert "Old Memo.doc" -o "Old Memo.docx"   # modernise an old file
```

Uses LibreOffice with bookmarks, tagged structure and a searchable text layer
switched on. Runs in a throw-away LibreOffice profile, so it does not fight with
any LibreOffice window you have open. Accepts `.docx .doc .odt .rtf .txt .html`
in; produces `.pdf .docx .odt .txt .html` out (chosen by the `-o` extension).

### `validate` — the gate

```bash
zlinuxdocs validate "Final Report.pdf"
zld check report.pdf --verbose
zlinuxdocs validate report.pdf --json
zlinuxdocs verify leaflet.pdf --no-bookmarks    # a one-page leaflet has no chapters
```

Checks that it really is a PDF and opens; is not password-protected; has pages;
has bookmarks; has selectable, searchable text; shows no leftover Word field
codes (`MERGEFORMAT`, `{ PAGE }`, `Error! Reference source not found`); and has
a sound internal structure.

**Exits non-zero when any check fails**, so it works in a script:

```bash
if zlinuxdocs validate report.pdf; then
  echo "ready to send"
fi
```

### `markers` — what the reviewer flagged

```bash
zlinuxdocs markers "Final Report v2 (1).docx"
zld todo report.docx --tsv -o markers.tsv
zlinuxdocs flags report.docx --marker "[TODO]"
```

Finds every `[V]` verification mark, in paragraphs **and inside table cells**,
and says which section each one sits under. Read-only — clearing a marker is
your decision, not the program's.

### `profile` — the house print settings

```bash
zlinuxdocs profile                     # a plain-language summary
zlinuxdocs settings --list             # release, draft, archive, screen
zlinuxdocs profile --show draft
zlinuxdocs profile -o my-profile.yaml  # copy it out to adjust
zlinuxdocs convert report.docx -o report.pdf --profile-file my-profile.yaml
```

A4 portrait, 25 mm margins with a 10 mm binding gutter, Liberation Serif body /
Liberation Sans headings, contents page to depth 3 with dot leaders, repeating
table headers, widow and orphan control. These are the settings from a real
16-volume government submission.

---

## Safety — it will not eat your document

* Nothing is written over your original unless you pass `--in-place`, and even
  then a `.bak` copy is kept beside it.
* An existing output file is never replaced without `--force`.
* `-o` pointing at the input file is refused.
* `--dry-run` is available on every command that writes.
* Missing parent folders are created for you.

```
$ zlinuxdocs fix-headings report.docx -o fixed.docx
zlinuxdocs: 'fixed.docx' already exists, and it will not be overwritten.

  What to do: either choose another name,
      -o "fixed-2.docx"
  or repeat the command with --force to replace the existing file.
```

You will never see a Python traceback. Every failure is one plain sentence plus
what to do about it, and where a package is missing it is named exactly:

```
$ zlinuxdocs convert report.docx -o report.pdf
zlinuxdocs: 'soffice' is not installed on this computer, and it is needed for
turning documents into PDF.

  What to do — install it with one command:
      sudo apt install libreoffice-writer
```

---

## Verb-availability matrix

Which commands still work when a dependency is absent. `bundled` means the
library ships inside the package, so its absence on your system cannot break
anything.

| command | python-docx | PyYAML | pypdf | python3-lxml | poppler-utils | qpdf | LibreOffice |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `--version`, `--help`, `quickstart`, `examples` | — | — | — | — | — | — | — |
| `inspect` | bundled | — | — | **required** | — | — | — |
| `fix-headings` | bundled | — | — | **required** | — | — | — |
| `markers` | — | — | — | — | — | — | — |
| `profile` | — | bundled | — | — | — | — | — |
| `convert` | — | bundled | — | — | — | — | **required** |
| `validate` | — | — | bundled | — | **required** | optional¹ | — |

¹ Without `qpdf`, `validate` skips the deep structural check, prints a one-line
note naming the package, and still runs every other check.

`markers` needs nothing at all beyond Python — it reads the `.docx` with the
standard library, so it works on the barest possible install.

**Package policy.** `python3 (>= 3.10)`, `python3-lxml` and `poppler-utils` are
hard dependencies. `qpdf` and `libreoffice-writer` are *Recommends*, so
`inspect` never drags in half a gigabyte of office suite. python-docx, PyYAML,
pypdf and typing_extensions are vendored under
`/usr/share/zlinuxdocs/vendor/` with their licences — nothing is fetched from
PyPI, ever, and PEP 668 ("externally managed environment") cannot bite you.

`python3-lxml` is a hard dependency because python-docx is built on it and
lxml is a compiled C extension, which cannot be vendored into an
`Architecture: all` package. It is a ~1.5 MB package present in every Debian
and Ubuntu release.

---

## PDF/A — read this before you promise anyone anything

**PDF/A conformance is not claimed.**

`convert --pdfa` asks LibreOffice to export in an archival PDF/A flavour. That
is a *request*. Nothing in this program can verify whether the result actually
conforms — doing that needs a dedicated validator such as
[veraPDF](https://verapdf.org/).

So: do not describe a file produced here as "certified PDF/A" on this
program's word. The `--help` text says the same thing, and so does
`zlinuxdocs profile`.

Other honest limits, inherited from the LibreOffice path:

* **Typography differs from Word.** Font metrics, line spacing and kerning
  shift slightly. Layout is close, not identical.
* **Complex Word features** — nested field codes, custom XML, macros — may not
  survive conversion.
* **Bookmarks come from heading styles.** If a document uses custom styles that
  are not recognised as headings, the chapter list will be incomplete. Run
  `zlinuxdocs inspect` first; it tells you when that is the case.

---

## The example documents

Installed at `/usr/share/zlinuxdocs/samples/` (see the `README.md` beside them,
or run `zlinuxdocs samples`). All generated; nothing in them is real.

| file | what it demonstrates |
|---|---|
| `plain-no-headings.docx` | The flagship case: headings that are only bold text, plus two traps that must *not* be promoted. |
| `proper-headings.docx` | Already correct — proves idempotency (0 promotions). |
| `mixed-tables.docx` | A 41-row table crossing a page break. |
| `with-markers.docx` | `[V]` marks in paragraphs and in table cells. |
| `unicode-heavy.docx` | Bengali, Kokborok, Devanagari, ₹ — proves non-Latin scripts survive. |
| `empty.docx` | Nothing in it. Must not crash. |
| `one-line.docx` | One sentence. Must not crash. |
| `weird name (final) v2.docx` | Spaces and brackets in the name. |

---

## Building from source

```bash
git clone https://github.com/zexp1/zlinuxdocs
cd zlinuxdocs
./build-deb.sh          # prints dist/zlinuxdocs_0.1.0_all.deb
bash tests/run.sh       # 120+ checks, non-zero exit if any fail
```

`build-deb.sh` needs only `dpkg-deb`, `python3`, `gzip` and `sed`. No `make`,
no `dpkg-buildpackage`, no `pip`, no network. It fails loudly on any problem,
regenerates the example documents, refuses to ship a package containing
`__pycache__` or a maintainer script, smoke-tests the staged program, and
prints the artifact path.

To test the *installed* command instead of the source tree:

```bash
ZLD=zlinuxdocs bash tests/run.sh
```

The version lives in one file, `VERSION`. `build-deb.sh` stamps it into
`zlinuxdocs/__version__.py`, `debian/control`, the changelog, the man page and
the `.deb` filename, and fails if the source file has drifted out of sync.

---

## Where it comes from

The logic here is not new — it is the manual pipeline that produced a real
16-volume government Detailed Project Report submission (57–150 pages and
40–128 bookmarks per volume, 16 of 16 passing validation), packaged so that
somebody who is not a programmer can use it. The heading-promotion, marker
triage, conversion and validation steps were all proven on that corpus before
they were given a front door.

## Licence

MIT. See [LICENSE](LICENSE). Vendored libraries keep their own licences
(python-docx MIT, PyYAML MIT, pypdf BSD-3-Clause, typing_extensions PSF-2.0);
the aggregated notice is in `debian/copyright`, installed to
`/usr/share/doc/zlinuxdocs/copyright`.

## Bugs

https://github.com/zexp1/zlinuxdocs/issues

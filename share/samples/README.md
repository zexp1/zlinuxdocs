# Example documents

These files ship with `zlinuxdocs` and are installed to
`/usr/share/zlinuxdocs/samples/`. They exist so you can try every command
before you risk a document of your own.

They were **generated** by `tools/make_samples.py`. Nothing in them is real —
no real place, person, scheme or figure appears anywhere.

New here? Run `zlinuxdocs quickstart` for a five-command walkthrough.

| file | what it demonstrates |
|---|---|
| `plain-no-headings.docx` | The flagship case. Lines that LOOK like headings ("1 - Introduction", "1.1 Scope") but are ordinary bold text. A PDF made from it has no chapter list. `fix-headings` rescues it. Also contains two traps that must NOT be promoted: a sentence starting "See 1.1 above", and a long paragraph beginning with "1.2". |
| `proper-headings.docx` | The same report, already correct. Proves idempotency: `fix-headings` reports 0 promotions. |
| `mixed-tables.docx` | Headings plus a 41-row table that runs across a page break, plus a second small table. Proves tables survive conversion. |
| `with-markers.docx` | Several `[V]` verification marks, both in paragraphs and inside table cells. Proves `markers` looks inside tables. |
| `unicode-heavy.docx` | Bengali, Kokborok, Devanagari, and typographic symbols (₹ — “ ” ½ ‰). Proves non-Latin scripts survive inspection and conversion without mojibake. |
| `empty.docx` | A document with nothing in it. Must not crash anything. |
| `one-line.docx` | A single sentence. The degenerate real-world case (a covering note). Must not crash anything. |
| `weird name (final) v2.docx` | Spaces and brackets in the file name. Proves quoting works end to end. |

## Try them

```bash
cd /tmp

# 1. Look inside the broken one
zlinuxdocs inspect "/usr/share/zlinuxdocs/samples/plain-no-headings.docx"

# 2. Repair it (the original is never touched)
zlinuxdocs fix-headings "/usr/share/zlinuxdocs/samples/plain-no-headings.docx" -o fixed.docx

# 3. Run it again on the result — 0 promotions, because it is already fixed
zlinuxdocs fix-headings fixed.docx --dry-run

# 4. Make the PDF and check it
zlinuxdocs convert fixed.docx -o fixed.pdf
zlinuxdocs validate fixed.pdf

# 5. The other samples
zlinuxdocs markers "/usr/share/zlinuxdocs/samples/with-markers.docx"
zlinuxdocs inspect "/usr/share/zlinuxdocs/samples/unicode-heavy.docx" --verbose
zlinuxdocs inspect "/usr/share/zlinuxdocs/samples/mixed-tables.docx"
zlinuxdocs inspect "/usr/share/zlinuxdocs/samples/empty.docx"
zlinuxdocs inspect "/usr/share/zlinuxdocs/samples/one-line.docx"
zlinuxdocs inspect "/usr/share/zlinuxdocs/samples/weird name (final) v2.docx"
```

A quick check that the broken sample really is broken: convert
`plain-no-headings.docx` straight to PDF without repairing it, and `validate`
will fail with "the PDF has no bookmarks". Repair it first and validate passes.
That contrast is the whole reason this tool exists.

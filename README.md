# linkrot

Tiny, dependency-free Markdown link checker. Written by an AI agent (Claude).

    python3 linkrot.py README.md docs/          # local files + #anchors
    python3 linkrot.py --online docs/           # also check http(s) URLs

Skips code blocks/spans and `mailto:`/`tel:`. Anchors follow GitHub-style slugs (duplicates get `-1`, `-2`).
Exit status is 1 if any problem is found. Tests: `pytest`.

<!-- toc -->

- [Options](#options)
- [More features (v0.2)](#more-features-v02)
- [GitHub Action](#github-action)
- [`--html-as-md`](#--html-as-md)

<!-- tocstop -->

## Options
- `--online` also check http(s) URLs
- `--json` machine-readable output
- `--ignore REGEX` skip matching targets (repeatable)

CI: see `docs/ci.yml.example` (copy to `.github/workflows/ci.yml`).

## More features (v0.2)

- Anchors also match HTML `id=` / `name=` attributes (e.g. `<a name="x"></a>`).
- Reference-style links (`[text][ref]`, `[ref][]`, `[ref]` with `[ref]: url`) are checked.
- URLs are checked in parallel (8 threads per file, each unique URL once).
- Config: a `.linkrot.toml` (or `--config FILE`, Python 3.11+) may set
  `online = true` and `ignore = ["regex", ...]`.
- Install: `pip install .` gives a `linkrot` command.

## GitHub Action

```yaml
- uses: actions/checkout@v4
- uses: maxotto-agent/linkrot@main
  with: { paths: ".", online: "false" }
```

## `--html-as-md`

For mdBook/Sphinx-style sources that link to the built `.html` page, `--html-as-md` (or `html_as_md = true` in config) resolves a missing `foo.html` to `foo.md` and checks its anchors. Footnote definitions (`[^1]: ...`) are ignored as reference definitions. Dogfooding on the Rust book source with this flag surfaced links whose target headings no longer exist.

## pre-commit

```yaml
repos:
  - repo: https://github.com/maxotto-agent/linkrot
    rev: v0.3.1
    hooks:
      - id: linkrot
```

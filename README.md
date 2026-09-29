# linkrot

Tiny, dependency-free Markdown link checker. Written by an AI agent (Claude).

    python3 linkrot.py README.md docs/          # local files + #anchors
    python3 linkrot.py --online docs/           # also check http(s) URLs

Skips code blocks/spans and `mailto:`/`tel:`. Anchors follow GitHub-style slugs (duplicates get `-1`, `-2`).
Exit status is 1 if any problem is found. Tests: `pytest`.

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

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

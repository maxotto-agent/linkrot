#!/usr/bin/env python3
"""linkrot: check Markdown files for broken local links, anchors and URLs."""
import argparse, json, re, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python < 3.11
    tomllib = None

LINK = re.compile(r'(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)|!\[[^\]]*\]\(([^)\s]+)\)')
HEAD = re.compile(r'^#{1,6}\s+(.*?)\s*#*\s*$')
HTML_ID = re.compile(r'<[a-zA-Z][^>]*?\b(?:id|name)\s*=\s*["\']([^"\']+)["\']')
REFDEF = re.compile(r'^\s{0,3}\[([^\]^][^\]]*)\]:\s*<?(\S+?)>?(?:\s+.*)?$')
REFUSE = re.compile(r'(?<!\!)\[[^\]]*\]\[([^\]]*)\]|(?<!\!)\[([^\]]+)\](?![\[(:])')
FENCE = re.compile(r'^\s*(```|~~~)')


def slug(text):
    text = re.sub(r'[`*_]', '', text.strip().lower())
    text = re.sub(r'[^\w\- ]', '', text)
    return text.replace(' ', '-')


def strip_code(text, inline=True):
    out, fenced = [], False
    for line in text.splitlines():
        if FENCE.match(line):
            fenced = not fenced
            out.append('')
        else:
            out.append('' if fenced else re.sub(r'`[^`]*`', '', line) if inline else line)
    return out


SETEXT = re.compile(r'^\s{0,3}(=+|-+)\s*$')


def anchors(path):
    seen, result = {}, set()
    lines = strip_code(path.read_text(encoding='utf-8', errors='replace'), inline=False)
    for idx, line in enumerate(lines):
        result.update(HTML_ID.findall(line))
        m = HEAD.match(line)
        if m:
            title = m.group(1)
        elif idx and SETEXT.match(line) and lines[idx - 1].strip() and not HEAD.match(lines[idx - 1]):
            title = lines[idx - 1].strip()
        else:
            continue
        s = slug(title)
        n = seen.get(s, 0)
        seen[s] = n + 1
        result.add(s if n == 0 else f'{s}-{n}')
    return result


def check_url(url, timeout=10):
    req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'linkrot/0.1'})
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            return None
    except urllib.error.HTTPError as e:
        if e.code in (403, 405, 501):  # HEAD refused; retry with GET
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'linkrot/0.1'})
                with urllib.request.urlopen(req, timeout=timeout):
                    return None
            except Exception as e2:
                return str(e2)
        return f'HTTP {e.code}'
    except Exception as e:
        return str(e)


def targets(lines):
    """Yield (lineno, target) for inline and reference-style links."""
    defs = {}
    for line in lines:
        m = REFDEF.match(line)
        if m:
            defs.setdefault(m.group(1).lower(), m.group(2))
    for i, line in enumerate(lines, 1):
        if REFDEF.match(line):
            continue
        for m in LINK.finditer(line):
            yield i, m.group(1) or m.group(2)
        for m in REFUSE.finditer(line):
            label = (m.group(1) or m.group(2) or '').lower()
            if m.group(1) is not None and not label:
                label = m.group(0)[1:m.group(0).index(']')].lower()
            if label in defs:
                yield i, defs[label]


def check_file(path, online=False, check=check_url, html_as_md=False):
    """Return list of (lineno, target, problem)."""
    problems = []
    lines = strip_code(path.read_text(encoding='utf-8', errors='replace'))
    urls = {t for _, t in targets(lines) if re.match(r'^https?://', t)} if online else set()
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = dict(zip(sorted(urls), ex.map(check, sorted(urls))))
    for i, target in targets(lines):
        if re.match(r'^(mailto:|tel:)', target):
            continue
        if re.match(r'^https?://', target):
            if online:
                err = results.get(target)
                if err:
                    problems.append((i, target, err))
            continue
        file_part, _, frag = target.partition('#')
        dest = path if not file_part else (path.parent / file_part.split('?')[0])
        if html_as_md and dest.suffix == '.html' and not dest.exists():
            dest = dest.with_suffix('.md')
        if not dest.exists():
            problems.append((i, target, 'file not found'))
        elif frag and dest.is_file() and dest.suffix.lower() in ('.md', '.markdown'):
            if frag.lower() not in {a.lower() for a in anchors(dest)}:
                problems.append((i, target, 'anchor not found'))
    return problems


def load_config(path):
    p = Path(path) if path else Path('.linkrot.toml')
    if not p.is_file():
        if path:
            sys.exit(f'linkrot: config not found: {path}')
        return {}
    if tomllib is None:
        sys.exit('linkrot: config files need Python 3.11+')
    return tomllib.loads(p.read_text(encoding='utf-8'))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('paths', nargs='+', help='Markdown files or directories')
    ap.add_argument('--online', action='store_true', help='also check http(s) URLs')
    ap.add_argument('--json', action='store_true', help='print problems as JSON')
    ap.add_argument('--ignore', action='append', default=[], metavar='REGEX',
                    help='skip targets matching REGEX (repeatable)')
    ap.add_argument('--html-as-md', action='store_true',
                    help='resolve links to missing .html files to the .md source (mdBook, Sphinx-style sites)')
    ap.add_argument('--config', metavar='FILE', help='TOML config (default: .linkrot.toml if present)')
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    a.online = a.online or cfg.get('online', False)
    ignore = [re.compile(r) for r in a.ignore + list(cfg.get('ignore', []))]
    files = []
    for p in map(Path, a.paths):
        files += sorted(p.rglob('*.md')) if p.is_dir() else [p]
    bad, report = 0, []
    for f in files:
        for ln, t, why in check_file(f, a.online, html_as_md=a.html_as_md or cfg.get('html_as_md', False)):
            if any(r.search(t) for r in ignore):
                continue
            report.append({'file': str(f), 'line': ln, 'target': t, 'problem': why})
            if not a.json:
                print(f'{f}:{ln}: {t}: {why}')
            bad += 1
    if a.json:
        print(json.dumps(report, indent=2))
    print(f'{len(files)} file(s), {bad} problem(s)', file=sys.stderr)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())

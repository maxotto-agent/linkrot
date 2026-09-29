#!/usr/bin/env python3
"""linkrot: check Markdown files for broken local links, anchors and URLs."""
import argparse, json, re, sys, urllib.request, urllib.error
from pathlib import Path

LINK = re.compile(r'(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)|!\[[^\]]*\]\(([^)\s]+)\)')
HEAD = re.compile(r'^#{1,6}\s+(.*?)\s*#*\s*$')
FENCE = re.compile(r'^\s*(```|~~~)')


def slug(text):
    text = re.sub(r'[`*_]', '', text.strip().lower())
    text = re.sub(r'[^\w\- ]', '', text)
    return text.replace(' ', '-')


def strip_code(text):
    out, fenced = [], False
    for line in text.splitlines():
        if FENCE.match(line):
            fenced = not fenced
            out.append('')
        else:
            out.append('' if fenced else re.sub(r'`[^`]*`', '', line))
    return out


def anchors(path):
    seen, result = {}, set()
    for line in strip_code(path.read_text(encoding='utf-8', errors='replace')):
        m = HEAD.match(line)
        if m:
            s = slug(m.group(1))
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


def check_file(path, online=False, check=check_url):
    """Return list of (lineno, target, problem)."""
    problems = []
    for i, line in enumerate(strip_code(path.read_text(encoding='utf-8', errors='replace')), 1):
        for m in LINK.finditer(line):
            target = m.group(1) or m.group(2)
            if re.match(r'^(mailto:|tel:)', target):
                continue
            if re.match(r'^https?://', target):
                if online:
                    err = check(target)
                    if err:
                        problems.append((i, target, err))
                continue
            file_part, _, frag = target.partition('#')
            dest = path if not file_part else (path.parent / file_part.split('?')[0])
            if not dest.exists():
                problems.append((i, target, 'file not found'))
            elif frag and dest.is_file() and dest.suffix.lower() in ('.md', '.markdown'):
                if frag.lower() not in anchors(dest):
                    problems.append((i, target, 'anchor not found'))
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('paths', nargs='+', help='Markdown files or directories')
    ap.add_argument('--online', action='store_true', help='also check http(s) URLs')
    ap.add_argument('--json', action='store_true', help='print problems as JSON')
    ap.add_argument('--ignore', action='append', default=[], metavar='REGEX',
                    help='skip targets matching REGEX (repeatable)')
    a = ap.parse_args(argv)
    ignore = [re.compile(r) for r in a.ignore]
    files = []
    for p in map(Path, a.paths):
        files += sorted(p.rglob('*.md')) if p.is_dir() else [p]
    bad, report = 0, []
    for f in files:
        for ln, t, why in check_file(f, a.online):
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

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
import linkrot


def test_all(tmp_path):
    (tmp_path / 'b.md').write_text('# Hello World\n## Dup\n## Dup\n')
    (tmp_path / 'a.md').write_text(
        '[ok](b.md#hello-world) [dup](b.md#dup-1) [bad](b.md#nope) [gone](c.md)\n'
        '[self](#top)\n# Top\n`[x](nothere.md)`\n```\n[y](nothere2.md)\n```\n'
        '[u](http://example.invalid/x) [m](mailto:a@b.c)\n')
    got = linkrot.check_file(tmp_path / 'a.md')
    assert [(g[1], g[2]) for g in got] == [('b.md#nope', 'anchor not found'), ('c.md', 'file not found')]
    got = linkrot.check_file(tmp_path / 'a.md', online=True, check=lambda u: 'boom')
    assert any(g[1].startswith('http') for g in got)


def test_main(tmp_path):
    (tmp_path / 'a.md').write_text('[x](missing.md)')
    assert linkrot.main([str(tmp_path)]) == 1


def test_json_and_ignore(tmp_path, capsys):
    import json
    f = tmp_path / 'a.md'
    f.write_text('[x](missing.md) [y](skip/me.md)\n')
    assert linkrot.main([str(f), '--json', '--ignore', '^skip/']) == 1
    data = json.loads(capsys.readouterr().out)
    assert [d['target'] for d in data] == ['missing.md']


def test_html_ids_and_reference_links(tmp_path):
    (tmp_path / 'b.md').write_text('<a name="old-id"></a>\n<h2 id="Sec">x</h2>\n')
    (tmp_path / 'a.md').write_text(
        '[a][r1] [b][r2] [c][] [d]\n\n[r1]: b.md#old-id\n[r2]: b.md#Sec\n[c]: gone.md\n[d]: b.md#nope\n')
    got = linkrot.check_file(tmp_path / 'a.md')
    assert [(g[1], g[2]) for g in got] == [('gone.md', 'file not found'), ('b.md#nope', 'anchor not found')]


def test_config(tmp_path, monkeypatch):
    (tmp_path / '.linkrot.toml').write_text('ignore = ["^skip/"]\n')
    (tmp_path / 'a.md').write_text('[y](skip/me.md)\n')
    monkeypatch.chdir(tmp_path)
    assert linkrot.main(['a.md']) == 0


def test_footnotes_and_html_as_md(tmp_path):
    (tmp_path / 'b.md').write_text('# Sec\n')
    (tmp_path / 'a.md').write_text('x[^1] [p](b.html#sec) [q](b.html#no)\n\n[^1]: [u](b.md)\n')
    assert [g[1] for g in linkrot.check_file(tmp_path / 'a.md')] == ['b.html#sec', 'b.html#no']
    got = linkrot.check_file(tmp_path / 'a.md', html_as_md=True)
    assert [(g[1], g[2]) for g in got] == [('b.html#no', 'anchor not found')]


def test_setext_headings(tmp_path):
    (tmp_path / 'b.md').write_text('Title Here\n==========\n\nSub Part\n--------\n')
    (tmp_path / 'a.md').write_text('[a](b.md#title-here) [b](b.md#sub-part)\n')
    assert linkrot.check_file(tmp_path / 'a.md') == []

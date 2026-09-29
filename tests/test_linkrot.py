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

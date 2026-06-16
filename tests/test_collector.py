from code_reviewer.collector import collect_files
from code_reviewer.config import Settings


def test_collect_filters_by_language(tmp_path):
    (tmp_path / "a.py").write_text("print('hi')\n")
    (tmp_path / "b.js").write_text("console.log('hi')\n")
    sub = tmp_path / "node_modules"
    sub.mkdir()
    (sub / "c.py").write_text("ignored = True\n")

    settings = Settings(path=str(tmp_path), language="python")
    files = collect_files(settings)

    rels = {f.relpath for f in files}
    assert rels == {"a.py"}  # b.js excluded, node_modules pruned


def test_truncation(tmp_path):
    big = "x = 1\n" * 10000
    (tmp_path / "big.py").write_text(big)
    settings = Settings(path=str(tmp_path), language="python", max_file_bytes=100)
    files = collect_files(settings)
    assert files[0].truncated is True
    assert len(files[0].content) <= 100

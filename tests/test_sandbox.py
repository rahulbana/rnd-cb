import pytest

from autodev.sandbox import SandboxManager, slugify


def test_slugify():
    assert slugify("My Cool App!") == "my-cool-app"
    assert slugify("   ") == "project"


def test_write_read_roundtrip():
    sm = SandboxManager("abcd1234ef00", "Round Trip")
    sm.create()
    sm.write_file("src/main.py", "print('hi')\n")
    assert sm.read_file("src/main.py") == "print('hi')\n"
    assert "src/main.py" in sm.list_files()


def test_path_escape_blocked():
    sm = SandboxManager("abcd1234ef01", "Escape")
    sm.create()
    with pytest.raises(ValueError):
        sm.write_file("../../etc/evil", "x")

import os

from product_intel.dotenv import find_dotenv, load_dotenv, parse_dotenv


def test_parse_basic_and_quotes_and_comments():
    text = (
        "# a comment\n"
        "\n"
        "OPENAI_API_KEY=sk-test123\n"
        'QUOTED="hello world"\n'
        "SINGLE='single'\n"
        "export EXPORTED=value\n"
        "INLINE=abc # trailing comment\n"
    )
    parsed = parse_dotenv(text)
    assert parsed["OPENAI_API_KEY"] == "sk-test123"
    assert parsed["QUOTED"] == "hello world"
    assert parsed["SINGLE"] == "single"
    assert parsed["EXPORTED"] == "value"
    assert parsed["INLINE"] == "abc"


def test_load_dotenv_sets_and_respects_precedence(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("OPENAI_API_KEY=from-file\nOTHER_VAR=xyz\n", encoding="utf-8")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OTHER_VAR", raising=False)

    loaded = load_dotenv(env)
    assert loaded == env
    assert os.environ["OPENAI_API_KEY"] == "from-file"
    assert os.environ["OTHER_VAR"] == "xyz"


def test_shell_env_wins_over_file(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("OPENAI_API_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "from-shell")
    load_dotenv(env)  # override=False by default
    assert os.environ["OPENAI_API_KEY"] == "from-shell"


def test_override_true_replaces(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("OPENAI_API_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "from-shell")
    load_dotenv(env, override=True)
    assert os.environ["OPENAI_API_KEY"] == "from-file"


def test_find_dotenv_searches_parents(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("A=1\n", encoding="utf-8")
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    found = find_dotenv()
    assert found == (tmp_path / ".env").resolve()


def test_load_dotenv_missing_returns_none(tmp_path):
    assert load_dotenv(tmp_path / "nope.env") is None

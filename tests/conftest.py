"""Test config. Point AutoDev at throwaway temp dirs BEFORE importing it."""
import os
import tempfile

# Must be set before any autodev import so the DB engine / workspace bind here.
_TMP = tempfile.mkdtemp(prefix="autodev-test-")
os.environ["AUTODEV_DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["AUTODEV_WORKSPACE_ROOT"] = f"{_TMP}/workspaces"
os.environ["AUTODEV_MEMORY_ENABLED"] = "false"
os.environ["AUTODEV_LLM_PROVIDER"] = "openai"
os.environ["AUTODEV_OPENAI_API_KEY"] = "test-key-not-used"
os.environ["AUTODEV_COMMAND_TIMEOUT"] = "180"

import pytest  # noqa: E402

from autodev.config import get_settings  # noqa: E402
from autodev.database import init_db  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _db():
    get_settings.cache_clear()
    init_db()
    yield

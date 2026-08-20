"""App package init.

Load environment variables from a local .env file (if present) as early as
possible, so os.getenv(...) calls elsewhere see them. Real environment
variables always take precedence over .env values.
"""
import os

try:
    from dotenv import load_dotenv

    # backend/.env sits one directory above this package.
    _env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    load_dotenv(_env_path, override=False)
except Exception:
    # python-dotenv is optional; env vars can also be set by the shell.
    pass

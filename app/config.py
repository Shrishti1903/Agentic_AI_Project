"""app/config.py - centralised environment / secret loading.

Load order:
  1. Real environment variables (e.g. set on the server / CI).
  2. .env file in the project root (local development).

The only secret this project currently needs is OPENAI_API_KEY.
"""
import os
from pathlib import Path

# Load .env from the project root (two levels up from this file)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=_env_path, override=False)
except ImportError:
    pass  # python-dotenv not installed; rely on real env vars


def get_openai_key():
    """Return the OpenAI API key, or None if not configured."""
    return os.getenv("OPENAI_API_KEY")


def require_openai_key():
    """Return the key or raise a clear RuntimeError if missing."""
    key = get_openai_key()
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. "
            "Create a .env file in the project root with:\n"
            "  OPENAI_API_KEY=sk-...your-key-here..."
        )
    return key

"""app/config.py - centralised environment / secret loading.

Load order:
  1. Real environment variables (e.g. set on the server / CI).
  2. .env file in the project root (local development).
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


def get_anthropic_key():
    """Return the Anthropic API key, or None if not configured."""
    return os.getenv("ANTHROPIC_API_KEY")


def get_anthropic_workspace_id():
    """Return the Anthropic Workspace ID, or None if not set.

    Required when using an org-level (non-workspace-scoped) API key.
    Find it at: console.anthropic.com/settings/workspaces
    """
    return os.getenv("ANTHROPIC_WORKSPACE_ID")


def get_openai_key():
    """Return the OpenAI API key, or None if not configured."""
    return os.getenv("OPENAI_API_KEY")

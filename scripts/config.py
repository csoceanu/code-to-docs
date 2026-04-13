"""
Centralized configuration for code-to-docs GitHub Action.

All environment variable access for configuration lives here.
Runtime env vars (GH_TOKEN, PR_NUMBER, etc.) are still read where needed.
"""

import os

from openai import OpenAI


def get_client():
    """Get the shared OpenAI-compatible client."""
    return OpenAI(
        base_url=os.environ["MODEL_API_BASE"],
        api_key=os.environ.get("MODEL_API_KEY") or "EMPTY",
    )


def get_model_name():
    """Get the configured model name."""
    return os.environ.get("MODEL_NAME", "default")


def get_docs_repo_url():
    """Get the documentation repository URL."""
    return os.environ.get("DOCS_REPO_URL", "")


def get_branch_name(pr_number=None):
    """Get the docs update branch name, unique per PR to avoid collisions."""
    if pr_number and pr_number != "unknown":
        return f"doc-update-from-pr-{pr_number}"
    return "doc-update-from-pr"

"""Shared fixtures for code-to-docs tests."""

import os
import sys
import pytest

# Add scripts/ to the path so we can import modules directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

# Config is now lazy (no env vars read at import time).
# Tests that need a configured client should set these env vars explicitly.


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure sensitive env vars are NOT set unless a test explicitly sets them."""
    for var in [
        "GH_TOKEN",
        "MODEL_API_KEY",
        "JIRA_API_TOKEN",
        "GOOGLE_SA_KEY",
        "MODEL_API_BASE",
        "MODEL_NAME",
        "DOCS_REPO_URL",
        "DOCS_SUBFOLDER",
        "DOCS_BASE_BRANCH",
        "PR_NUMBER",
        "PR_BASE",
        "COMMENT_BODY",
    ]:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def tmp_tree(tmp_path):
    """Create a temporary directory tree for path validation tests."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("# Guide")
    (docs / "ref.adoc").write_text("= Reference")
    (docs / "tutorial.rst").write_text("Tutorial\n========")
    sub = docs / "sub"
    sub.mkdir()
    (sub / "nested.md").write_text("# Nested")
    return tmp_path

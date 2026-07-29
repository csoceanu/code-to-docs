"""Tests for github_ops.py — diff retrieval, commit info, and docs setup."""

import sys
from unittest.mock import MagicMock, patch

sys.modules.setdefault("openai", MagicMock())

from github_ops import get_commit_info, get_diff, setup_docs_environment


def _mock_run(stdout="", returncode=0, stderr=""):
    result = MagicMock()
    result.stdout = stdout
    result.returncode = returncode
    result.stderr = stderr
    return result


# ── get_diff ─────────────────────────────────────────────────────────────────


class TestGetDiff:
    def test_merge_base_success(self, monkeypatch):
        monkeypatch.setenv("PR_BASE", "origin/main")
        monkeypatch.setenv("PR_NUMBER", "42")

        calls = []

        def mock_run(cmd, **kwargs):
            calls.append(cmd)
            if "merge-base" in cmd:
                return _mock_run(stdout="abc123def456")
            if "--name-only" in cmd:
                return _mock_run(stdout="src/foo.py\nsrc/bar.py")
            if "diff" in cmd:
                return _mock_run(stdout="diff --git a/foo.py b/foo.py\n+new line")
            return _mock_run()

        with patch("github_ops.run_command_safe", side_effect=mock_run):
            result = get_diff()

        assert "new line" in result

    def test_merge_base_fallback(self, monkeypatch):
        monkeypatch.setenv("PR_BASE", "origin/main")
        monkeypatch.setenv("PR_NUMBER", "42")

        def mock_run(cmd, **kwargs):
            if "merge-base" in cmd:
                return _mock_run(returncode=1)
            return _mock_run(stdout="fallback diff content")

        with patch("github_ops.run_command_safe", side_effect=mock_run):
            result = get_diff()

        assert "fallback diff content" in result

    def test_error_returns_empty(self, monkeypatch):
        monkeypatch.setenv("PR_BASE", "origin/main")
        monkeypatch.setenv("PR_NUMBER", "1")

        with patch("github_ops.run_command_safe", side_effect=Exception("git error")):
            result = get_diff()

        assert result == ""


# ── get_commit_info ──────────────────────────────────────────────────────────


class TestGetCommitInfo:
    def test_basic_info(self, monkeypatch):
        monkeypatch.delenv("PR_NUMBER", raising=False)

        def mock_run(cmd, **kwargs):
            if "rev-parse" in cmd:
                return _mock_run(stdout="abc123def456789")
            if "remote.origin.url" in cmd:
                return _mock_run(stdout="https://github.com/org/repo.git")
            return _mock_run()

        with patch("github_ops.run_command_safe", side_effect=mock_run):
            result = get_commit_info()

        assert result["repo_url"] == "https://github.com/org/repo"
        assert result["short_hash"] == "abc123d"
        assert "pr_number" not in result

    def test_with_pr_number(self, monkeypatch):
        monkeypatch.setenv("PR_NUMBER", "42")

        def mock_run(cmd, **kwargs):
            if "rev-parse" in cmd:
                return _mock_run(stdout="abc123def456789")
            if "remote.origin.url" in cmd:
                return _mock_run(stdout="https://github.com/org/repo")
            return _mock_run()

        with patch("github_ops.run_command_safe", side_effect=mock_run):
            result = get_commit_info()

        assert result["pr_number"] == "42"
        assert result["pr_url"] == "https://github.com/org/repo/pull/42"

    def test_ssh_url_converted(self, monkeypatch):
        monkeypatch.delenv("PR_NUMBER", raising=False)

        def mock_run(cmd, **kwargs):
            if "rev-parse" in cmd:
                return _mock_run(stdout="abc123def456789")
            if "remote.origin.url" in cmd:
                return _mock_run(stdout="git@github.com:org/repo.git")
            return _mock_run()

        with patch("github_ops.run_command_safe", side_effect=mock_run):
            result = get_commit_info()

        assert result["repo_url"] == "https://github.com/org/repo"

    def test_rev_parse_fails(self, monkeypatch):
        monkeypatch.delenv("PR_NUMBER", raising=False)

        with patch("github_ops.run_command_safe", return_value=_mock_run(returncode=1)):
            result = get_commit_info()

        assert result is None

    def test_exception_returns_none(self, monkeypatch):
        monkeypatch.delenv("PR_NUMBER", raising=False)

        with patch("github_ops.run_command_safe", side_effect=Exception("fail")):
            result = get_commit_info()

        assert result is None


# ── setup_docs_environment ───────────────────────────────────────────────────


class TestSetupDocsEnvironment:
    def test_subfolder_exists(self, tmp_path, monkeypatch):
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DOCS_SUBFOLDER", "docs")
        monkeypatch.delenv("PR_NUMBER", raising=False)

        result = setup_docs_environment()
        assert result is True

    def test_subfolder_not_found(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DOCS_SUBFOLDER", "nonexistent_docs")
        monkeypatch.delenv("PR_NUMBER", raising=False)

        result = setup_docs_environment()
        assert result is False

    def test_subfolder_invalid_path(self, monkeypatch):
        monkeypatch.setenv("DOCS_SUBFOLDER", "../../etc")
        monkeypatch.delenv("PR_NUMBER", raising=False)

        result = setup_docs_environment()
        assert result is False

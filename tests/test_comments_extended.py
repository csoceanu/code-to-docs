"""Tests for comments.py — URL generation, parsing, and comment posting."""

import json
import sys
from unittest.mock import MagicMock, patch

sys.modules.setdefault("openai", MagicMock())

from comments import (
    _resolve_file_instructions,
    generate_file_summary,
    generate_summary_explanation,
    get_docs_file_url,
    parse_previous_review,
    post_review_comment,
)

# ── get_docs_file_url ───────────────────────────────────────────────────────


class TestGetDocsFileUrl:
    def test_same_repo_with_subfolder(self, monkeypatch):
        monkeypatch.setenv("DOCS_SUBFOLDER", "docs")
        monkeypatch.setenv("DOCS_BASE_BRANCH", "main")
        commit_info = {"repo_url": "https://github.com/org/repo"}
        url = get_docs_file_url("guide.rst", commit_info)
        assert url == "https://github.com/org/repo/blob/main/docs/guide.rst"

    def test_same_repo_file_already_has_subfolder(self, monkeypatch):
        monkeypatch.setenv("DOCS_SUBFOLDER", "docs")
        monkeypatch.setenv("DOCS_BASE_BRANCH", "main")
        commit_info = {"repo_url": "https://github.com/org/repo"}
        url = get_docs_file_url("docs/guide.rst", commit_info)
        assert url == "https://github.com/org/repo/blob/main/docs/guide.rst"

    def test_separate_repo_https(self, monkeypatch):
        monkeypatch.delenv("DOCS_SUBFOLDER", raising=False)
        monkeypatch.setenv("DOCS_BASE_BRANCH", "main")
        monkeypatch.setenv("DOCS_REPO_URL", "https://github.com/org/docs.git")
        url = get_docs_file_url("guide.rst")
        assert url == "https://github.com/org/docs/blob/main/guide.rst"

    def test_separate_repo_ssh(self, monkeypatch):
        monkeypatch.delenv("DOCS_SUBFOLDER", raising=False)
        monkeypatch.setenv("DOCS_BASE_BRANCH", "main")
        monkeypatch.setenv("DOCS_REPO_URL", "git@github.com:org/docs.git")
        url = get_docs_file_url("guide.rst")
        assert url == "https://github.com/org/docs/blob/main/guide.rst"

    def test_no_repo_url(self, monkeypatch):
        monkeypatch.delenv("DOCS_SUBFOLDER", raising=False)
        monkeypatch.delenv("DOCS_REPO_URL", raising=False)
        url = get_docs_file_url("guide.rst")
        assert url is None


# ── _resolve_file_instructions ───────────────────────────────────────────────


class TestResolveFileInstructions:
    def test_exact_match(self):
        result = _resolve_file_instructions(
            "docs/admin/config.rst", {"docs/admin/config.rst": "update CLI section"}
        )
        assert result == "update CLI section"

    def test_basename_match(self):
        result = _resolve_file_instructions(
            "docs/admin/config.rst", {"config.rst": "update CLI section"}
        )
        assert result == "update CLI section"

    def test_suffix_match(self):
        result = _resolve_file_instructions(
            "docs/admin/config.rst", {"admin/config.rst": "update CLI section"}
        )
        assert result == "update CLI section"

    def test_no_match(self):
        result = _resolve_file_instructions("docs/admin/config.rst", {"other.rst": "something"})
        assert result == ""

    def test_empty_instructions(self):
        result = _resolve_file_instructions("docs/guide.rst", {})
        assert result == ""

    def test_none_instructions(self):
        result = _resolve_file_instructions("docs/guide.rst", None)
        assert result == ""


# ── parse_previous_review ────────────────────────────────────────────────────


class TestParsePreviousReview:
    def test_no_gh_token(self, monkeypatch):
        monkeypatch.delenv("GH_TOKEN", raising=False)
        result = parse_previous_review("42")
        assert result["review_found"] is False

    def test_no_pr_number(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "test-token")
        result = parse_previous_review(None)
        assert result["review_found"] is False

    def test_unknown_pr_number(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "test-token")
        result = parse_previous_review("unknown")
        assert result["review_found"] is False

    def test_gh_command_fails(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "test-token")
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error"
        with patch("comments.run_command_safe", return_value=mock_result):
            result = parse_previous_review("42")
        assert result["review_found"] is False

    def test_parses_checked_files(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "test-token")
        review_body = (
            "## 📚 Documentation Review\n\n"
            "### 📋 Select files to update\n\n"
            "- [x] [guide.rst](https://example.com): Update guide\n"
            "- [ ] [api.md](https://example.com): Update API docs\n"
            "- [x] **config.rst**: Update config\n\n"
            "Latest commit: `abc1234`"
        )
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"comments": [{"body": review_body}]})
        with patch("comments.run_command_safe", return_value=mock_result):
            result = parse_previous_review("42")
        assert result["review_found"] is True
        assert "guide.rst" in result["accepted_files"]
        assert "config.rst" in result["accepted_files"]
        assert "api.md" in result["rejected_files"]
        assert result["review_commit"] == "abc1234"

    def test_no_review_comment_found(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "test-token")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"comments": [{"body": "Just a regular comment"}]})
        with patch("comments.run_command_safe", return_value=mock_result):
            result = parse_previous_review("42")
        assert result["review_found"] is False


# ── post_review_comment ──────────────────────────────────────────────────────


class TestPostReviewComment:
    def test_no_pr_number(self):
        result = post_review_comment([], None)
        assert result is False

    def test_unknown_pr_number(self):
        result = post_review_comment([], "unknown")
        assert result is False

    def test_no_gh_token(self, monkeypatch):
        monkeypatch.delenv("GH_TOKEN", raising=False)
        result = post_review_comment([], "42")
        assert result is False

    def test_empty_files_posts_success(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "test-token")
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("comments.run_command_safe", return_value=mock_result):
            result = post_review_comment([], "42")
        assert result is True

    def test_post_failure(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "test-token")
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "forbidden"
        with patch("comments.run_command_safe", return_value=mock_result):
            result = post_review_comment([], "42")
        assert result is False

    def test_post_with_files_and_content(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "test-token")
        monkeypatch.delenv("DOCS_SUBFOLDER", raising=False)
        monkeypatch.delenv("DOCS_REPO_URL", raising=False)

        files = [
            ("guide.rst", "old content", "new content"),
            ("api.md", "old api", "new api"),
        ]
        commit_info = {"short_hash": "abc1234", "repo_url": "https://github.com/org/repo"}

        mock_gh = MagicMock()
        mock_gh.returncode = 0

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Updated guide documentation"
        mock_client.chat.completions.create.return_value = mock_response

        with (
            patch("comments.run_command_safe", return_value=mock_gh),
            patch("comments.get_client", return_value=mock_client),
            patch("comments.get_model_name", return_value="test-model"),
        ):
            result = post_review_comment(files, "42", commit_info=commit_info)
        assert result is True

    def test_post_with_files_all_skipped(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "test-token")
        monkeypatch.delenv("DOCS_SUBFOLDER", raising=False)
        monkeypatch.delenv("DOCS_REPO_URL", raising=False)

        files = [("guide.rst", "same content", "same content")]

        mock_gh = MagicMock()
        mock_gh.returncode = 0

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "SKIP"
        mock_client.chat.completions.create.return_value = mock_response

        with (
            patch("comments.run_command_safe", return_value=mock_gh),
            patch("comments.get_client", return_value=mock_client),
            patch("comments.get_model_name", return_value="test-model"),
        ):
            result = post_review_comment(files, "42")
        assert result is True

    def test_post_with_feature_section(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "test-token")
        mock_gh = MagicMock()
        mock_gh.returncode = 0
        with patch("comments.run_command_safe", return_value=mock_gh):
            result = post_review_comment([], "42", feature_section="## Feature Coverage\nAll good")
        assert result is True

    def test_post_exception_handling(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "test-token")
        with patch("comments.run_command_safe", side_effect=Exception("network error")):
            result = post_review_comment([], "42")
        assert result is False


# ── generate_file_summary ────────────────────────────────────────────────────


class TestGenerateFileSummary:
    def test_returns_summary(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "I suggest updating the API reference section."
        mock_client.chat.completions.create.return_value = mock_response

        with (
            patch("comments.get_client", return_value=mock_client),
            patch("comments.get_model_name", return_value="test-model"),
        ):
            result = generate_file_summary("api.rst", "old docs", "new docs")
        assert "API reference" in result

    def test_collapses_whitespace(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Line one.\nLine two.\nLine three."
        mock_client.chat.completions.create.return_value = mock_response

        with (
            patch("comments.get_client", return_value=mock_client),
            patch("comments.get_model_name", return_value="test-model"),
        ):
            result = generate_file_summary("guide.md", "old", "new")
        assert "\n" not in result

    def test_error_returns_empty(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API down")

        with (
            patch("comments.get_client", return_value=mock_client),
            patch("comments.get_model_name", return_value="test-model"),
        ):
            result = generate_file_summary("guide.md", "old", "new")
        assert result == ""

    def test_new_file_no_original(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "New file with getting started guide."
        mock_client.chat.completions.create.return_value = mock_response

        with (
            patch("comments.get_client", return_value=mock_client),
            patch("comments.get_model_name", return_value="test-model"),
        ):
            result = generate_file_summary("new.md", "", "# Getting Started")
        assert "getting started" in result.lower()


# ── generate_summary_explanation ─────────────────────────────────────────────


class TestGenerateSummaryExplanation:
    def test_generates_summaries(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Updated the installation section."
        mock_client.chat.completions.create.return_value = mock_response

        files = [
            ("guide.rst", "old guide", "new guide"),
            ("api.md", "old api", "new api"),
        ]

        with (
            patch("comments.get_client", return_value=mock_client),
            patch("comments.get_model_name", return_value="test-model"),
            patch("comments.get_docs_file_url", return_value=None),
        ):
            summary, filtered = generate_summary_explanation(files)
        assert len(filtered) == 2
        assert "guide.rst" in summary
        assert "api.md" in summary

    def test_filters_skip_responses(self):
        call_count = [0]

        def mock_create(**kwargs):
            call_count[0] += 1
            mock_resp = MagicMock()
            mock_resp.choices = [MagicMock()]
            if call_count[0] == 1:
                mock_resp.choices[0].message.content = "Updated the guide."
            else:
                mock_resp.choices[0].message.content = "SKIP"
            return mock_resp

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = mock_create

        files = [
            ("guide.rst", "old", "new"),
            ("unchanged.md", "same", "same"),
        ]

        with (
            patch("comments.get_client", return_value=mock_client),
            patch("comments.get_model_name", return_value="test-model"),
            patch("comments.get_docs_file_url", return_value=None),
        ):
            summary, filtered = generate_summary_explanation(files)
        assert len(filtered) == 1

    def test_empty_files(self):
        summary, filtered = generate_summary_explanation([])
        assert summary == ""
        assert filtered == []

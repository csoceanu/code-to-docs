"""Tests for jira_integration.py — helper functions and formatting."""

import sys
from unittest.mock import MagicMock, patch

# Stub external dependencies before importing
sys.modules.setdefault("openai", MagicMock())
sys.modules.setdefault("mcp", MagicMock())
sys.modules.setdefault("mcp.client.stdio", MagicMock())

from jira_integration import (
    _build_mcp_env,
    _extract_google_doc_id,
    _extract_text,
    _find_all_links,
    _is_gws_configured,
    analyze_feature_coverage,
    format_feature_review_section,
    parse_feature_command,
)

# ── _build_mcp_env ──────────────────────────────────────────────────────────


class TestBuildMcpEnv:
    def test_basic_jira_only(self, monkeypatch):
        monkeypatch.setenv("JIRA_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_USERNAME", "user@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "secret-token")
        monkeypatch.delenv("CONFLUENCE_URL", raising=False)

        env = _build_mcp_env()
        assert env["READ_ONLY_MODE"] == "true"
        assert env["JIRA_URL"] == "https://jira.example.com"
        assert env["JIRA_USERNAME"] == "user@example.com"
        assert env["JIRA_API_TOKEN"] == "secret-token"
        assert "CONFLUENCE_URL" not in env

    def test_with_confluence(self, monkeypatch):
        monkeypatch.setenv("JIRA_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_USERNAME", "user@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "secret-token")
        monkeypatch.setenv("CONFLUENCE_URL", "https://wiki.example.com")

        env = _build_mcp_env()
        assert env["CONFLUENCE_URL"] == "https://wiki.example.com"
        assert env["CONFLUENCE_USERNAME"] == "user@example.com"
        assert env["CONFLUENCE_API_TOKEN"] == "secret-token"

    def test_confluence_separate_credentials(self, monkeypatch):
        monkeypatch.setenv("JIRA_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_USERNAME", "jira-user")
        monkeypatch.setenv("JIRA_API_TOKEN", "jira-token")
        monkeypatch.setenv("CONFLUENCE_URL", "https://wiki.example.com")
        monkeypatch.setenv("CONFLUENCE_USERNAME", "wiki-user")
        monkeypatch.setenv("CONFLUENCE_API_TOKEN", "wiki-token")

        env = _build_mcp_env()
        assert env["CONFLUENCE_USERNAME"] == "wiki-user"
        assert env["CONFLUENCE_API_TOKEN"] == "wiki-token"


# ── _extract_text ────────────────────────────────────────────────────────────


class TestExtractText:
    def test_extracts_text_blocks(self):
        block1 = MagicMock()
        block1.text = "Hello"
        block2 = MagicMock()
        block2.text = "World"
        assert _extract_text([block1, block2]) == "Hello\nWorld"

    def test_skips_empty_blocks(self):
        block1 = MagicMock()
        block1.text = "Hello"
        block2 = MagicMock()
        block2.text = ""
        assert _extract_text([block1, block2]) == "Hello"

    def test_empty_list(self):
        assert _extract_text([]) == ""

    def test_no_text_attribute(self):
        block = MagicMock(spec=[])
        assert _extract_text([block]) == ""


# ── _is_gws_configured ──────────────────────────────────────────────────────


class TestIsGwsConfigured:
    def test_not_configured_no_env(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE", raising=False)
        assert _is_gws_configured() is False

    def test_not_configured_no_binary(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE", "/tmp/creds.json")
        with patch("shutil.which", return_value=None):
            assert _is_gws_configured() is False

    def test_configured(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE", "/tmp/creds.json")
        with patch("shutil.which", return_value="/usr/local/bin/gws"):
            assert _is_gws_configured() is True


# ── _extract_google_doc_id ───────────────────────────────────────────────────


class TestExtractGoogleDocId:
    def test_google_doc(self):
        url = "https://docs.google.com/document/d/1abc_DEF-123/edit"
        doc_id, doc_type = _extract_google_doc_id(url)
        assert doc_id == "1abc_DEF-123"
        assert doc_type == "document"

    def test_google_slides(self):
        url = "https://docs.google.com/presentation/d/1abc_DEF-123/edit"
        doc_id, doc_type = _extract_google_doc_id(url)
        assert doc_id == "1abc_DEF-123"
        assert doc_type == "presentation"

    def test_google_sheets(self):
        url = "https://docs.google.com/spreadsheets/d/1abc_DEF-123/edit"
        doc_id, doc_type = _extract_google_doc_id(url)
        assert doc_id == "1abc_DEF-123"
        assert doc_type == "spreadsheet"

    def test_not_a_google_url(self):
        doc_id, doc_type = _extract_google_doc_id("https://example.com/page")
        assert doc_id is None
        assert doc_type is None

    def test_empty_string(self):
        doc_id, doc_type = _extract_google_doc_id("")
        assert doc_id is None
        assert doc_type is None


# ── _find_all_links ──────────────────────────────────────────────────────────


class TestFindAllLinks:
    def test_confluence_links(self):
        text = "See https://wiki.example.com/wiki/spaces/TEAM/pages/12345 for details"
        links = _find_all_links(text)
        assert "12345" in links["confluence_page_ids"]

    def test_confluence_page_id_param(self):
        text = "Link: https://wiki.example.com/page?pageId=67890"
        links = _find_all_links(text)
        assert "67890" in links["confluence_page_ids"]

    def test_google_docs_links(self):
        text = "Spec: https://docs.google.com/document/d/1abc_DEF/edit"
        links = _find_all_links(text)
        assert len(links["google_docs_urls"]) == 1
        assert "1abc_DEF" in links["google_docs_urls"][0]

    def test_deduplicates_google_docs(self):
        text = (
            "See https://docs.google.com/document/d/1abc/edit "
            "and https://docs.google.com/document/d/1abc/edit again"
        )
        links = _find_all_links(text)
        assert len(links["google_docs_urls"]) == 1

    def test_other_urls(self):
        text = "Check https://github.com/org/repo for source"
        links = _find_all_links(text)
        assert len(links["other_urls"]) == 1
        assert "github.com" in links["other_urls"][0]

    def test_skips_avatar_urls(self):
        text = "User https://gravatar.com/avatar/abc123 posted"
        links = _find_all_links(text)
        assert len(links["other_urls"]) == 0

    def test_empty_text(self):
        links = _find_all_links("")
        assert links["confluence_page_ids"] == []
        assert links["google_docs_urls"] == []
        assert links["other_urls"] == []

    def test_mixed_links(self):
        text = (
            "Jira: https://jira.example.com/browse/PROJ-1 "
            "Wiki: https://wiki.example.com/wiki/spaces/X/pages/111 "
            "Doc: https://docs.google.com/document/d/abc/edit"
        )
        links = _find_all_links(text)
        assert "111" in links["confluence_page_ids"]
        assert len(links["google_docs_urls"]) == 1
        assert len(links["other_urls"]) == 1


# ── parse_feature_command ────────────────────────────────────────────────────


class TestParseFeatureCommand:
    def test_basic_key(self):
        key, instructions = parse_feature_command("[review-feature] PROJ-123")
        assert key == "PROJ-123"
        assert instructions == ""

    def test_key_with_instructions(self):
        key, instructions = parse_feature_command("[review-feature] PROJ-456 focus on security")
        assert key == "PROJ-456"
        assert instructions == "focus on security"

    def test_case_insensitive(self):
        key, _ = parse_feature_command("[Review-Feature] proj-789")
        assert key == "PROJ-789"

    def test_no_key(self):
        key, instructions = parse_feature_command("[review-feature]")
        assert key is None
        assert instructions is None

    def test_not_a_feature_command(self):
        key, instructions = parse_feature_command("[review-docs]")
        assert key is None
        assert instructions is None


# ── format_feature_review_section ────────────────────────────────────────────


class TestFormatFeatureReviewSection:
    def test_basic_formatting(self, monkeypatch):
        monkeypatch.setenv("JIRA_URL", "https://jira.example.com")
        result = format_feature_review_section(
            "PROJ-123", "Add login page", "All requirements covered."
        )
        assert "PROJ-123" in result
        assert "Add login page" in result
        assert "All requirements covered." in result
        assert "jira.example.com/browse/PROJ-123" in result

    def test_with_inaccessible_links(self, monkeypatch):
        monkeypatch.setenv("JIRA_URL", "https://jira.example.com")
        result = format_feature_review_section(
            "PROJ-123",
            "Feature",
            "Analysis here",
            inaccessible_links=["Google Doc (url): permission denied"],
        )
        assert "Documents Not Accessible" in result
        assert "permission denied" in result

    def test_no_jira_url(self, monkeypatch):
        monkeypatch.delenv("JIRA_URL", raising=False)
        result = format_feature_review_section("PROJ-123", "Feature", "Analysis")
        assert "**PROJ-123**" in result


# ── analyze_feature_coverage ─────────────────────────────────────────────────


class TestAnalyzeFeatureCoverage:
    def test_returns_analysis(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "## Requirements Found\nREQ-1: Login page"
        mock_client.chat.completions.create.return_value = mock_response

        jira_context = {
            "issue_key": "PROJ-123",
            "raw_ticket": "Add login page with SSO",
            "spec_docs": [],
            "inaccessible_links": [],
        }

        result = analyze_feature_coverage(
            "diff --git a/login.py\n+def login():", jira_context, mock_client, "test-model"
        )
        assert "Requirements Found" in result

    def test_with_spec_docs(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Coverage: 80%"
        mock_client.chat.completions.create.return_value = mock_response

        jira_context = {
            "issue_key": "PROJ-123",
            "raw_ticket": "Feature description",
            "spec_docs": [
                {"source": "confluence", "title": "Design Doc", "content": "Spec content here"}
            ],
            "inaccessible_links": ["Google Doc (url): not accessible"],
        }

        result = analyze_feature_coverage("diff content", jira_context, mock_client, "test-model")
        assert "Coverage: 80%" in result

    def test_context_too_large(self):
        jira_context = {
            "issue_key": "PROJ-123",
            "raw_ticket": "x" * 500000,
            "spec_docs": [],
            "inaccessible_links": [],
        }

        result = analyze_feature_coverage("x" * 500000, jira_context, MagicMock(), "test-model")
        assert "exceeds the context budget" in result

    def test_llm_error(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API error")

        jira_context = {
            "issue_key": "PROJ-123",
            "raw_ticket": "Short description",
            "spec_docs": [],
            "inaccessible_links": [],
        }

        with patch("jira_integration.check_context_error"):
            result = analyze_feature_coverage("small diff", jira_context, mock_client, "test-model")
        assert "Error" in result

    def test_with_user_instructions(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Focused analysis"
        mock_client.chat.completions.create.return_value = mock_response

        jira_context = {
            "issue_key": "PROJ-123",
            "raw_ticket": "Description",
            "spec_docs": [],
            "inaccessible_links": [],
        }

        result = analyze_feature_coverage(
            "diff",
            jira_context,
            mock_client,
            "test-model",
            user_instructions="Focus on API changes",
        )
        assert "Focused analysis" in result
        call_args = mock_client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "Focus on API changes" in prompt

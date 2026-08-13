"""Tests for doc_index.py — folder discovery, hashing, manifest, and index management."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.modules.setdefault("openai", MagicMock())

from doc_index import (
    ROOT_LEVEL_FOLDER,
    folder_needs_reindex,
    get_doc_folders,
    get_docs_in_folder,
    get_docs_root,
    get_folder_doc_hashes,
    hash_file,
    load_all_indexes,
    load_index,
    load_manifest,
    save_index,
    save_manifest,
    working_directory,
)

# ── working_directory ────────────────────────────────────────────────────────


class TestWorkingDirectory:
    def test_changes_and_restores(self, tmp_path):
        original = os.getcwd()
        with working_directory(tmp_path):
            assert os.getcwd() == str(tmp_path)
        assert os.getcwd() == original

    def test_restores_on_exception(self, tmp_path):
        original = os.getcwd()
        try:
            with working_directory(tmp_path):
                raise ValueError("test error")
        except ValueError:
            pass
        assert os.getcwd() == original


# ── hash_file ────────────────────────────────────────────────────────────────


class TestHashFile:
    def test_consistent_hash(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        h1 = hash_file(f)
        h2 = hash_file(f)
        assert h1 == h2
        assert len(h1) == 64

    def test_different_content_different_hash(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("hello")
        f2.write_text("world")
        assert hash_file(f1) != hash_file(f2)


# ── get_docs_root ────────────────────────────────────────────────────────────


class TestGetDocsRoot:
    def test_default_current_dir(self, monkeypatch):
        monkeypatch.delenv("DOCS_SUBFOLDER", raising=False)
        result = get_docs_root()
        assert result == Path(".")

    def test_subfolder_exists(self, tmp_path, monkeypatch):
        docs = tmp_path / "docs"
        docs.mkdir()
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DOCS_SUBFOLDER", "docs")
        result = get_docs_root()
        assert result == Path("docs")

    def test_subfolder_not_found_falls_back(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DOCS_SUBFOLDER", "nonexistent")
        result = get_docs_root()
        assert result == Path(".")


# ── get_doc_folders ──────────────────────────────────────────────────────────


class TestGetDocFolders:
    def test_finds_folders(self, doc_tree):
        folders = get_doc_folders(doc_tree)
        assert "guides/operations" in folders
        assert "guides/configuration" in folders
        assert "tutorials" in folders

    def test_root_level_docs(self, doc_tree):
        folders = get_doc_folders(doc_tree)
        assert ROOT_LEVEL_FOLDER in folders

    def test_skips_hidden_and_underscore(self, doc_tree):
        folders = get_doc_folders(doc_tree)
        assert not any("_build" in f for f in folders)
        assert not any(".hidden" in f for f in folders)

    def test_empty_directory(self, tmp_path):
        folders = get_doc_folders(tmp_path)
        assert folders == []


# ── get_docs_in_folder ───────────────────────────────────────────────────────


class TestGetDocsInFolder:
    def test_gets_docs_in_subfolder(self, doc_tree):
        docs = get_docs_in_folder("guides/operations", doc_tree)
        names = {d.name for d in docs}
        assert "health-checks.rst" in names
        assert "monitoring.rst" in names

    def test_root_level_folder(self, doc_tree):
        docs = get_docs_in_folder(ROOT_LEVEL_FOLDER, doc_tree)
        names = {d.name for d in docs}
        assert "overview.rst" in names
        assert "README.md" in names

    def test_nonexistent_folder(self, doc_tree):
        docs = get_docs_in_folder("nonexistent", doc_tree)
        assert docs == []


# ── get_folder_doc_hashes ────────────────────────────────────────────────────


class TestGetFolderDocHashes:
    def test_hashes_docs(self, doc_tree):
        hashes = get_folder_doc_hashes("guides/operations", doc_tree)
        assert len(hashes) == 2
        for _path, h in hashes.items():
            assert len(h) == 64

    def test_empty_folder(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        hashes = get_folder_doc_hashes("empty", tmp_path)
        assert hashes == {}


# ── load_manifest / save_manifest ────────────────────────────────────────────


class TestManifest:
    def test_load_empty(self, tmp_path):
        manifest = load_manifest(tmp_path)
        assert manifest["version"] == "1.0"
        assert "folders" in manifest

    def test_save_and_load(self, tmp_path):
        manifest = {"version": "1.0", "folders": {"guides": {"doc_hashes": {"a.rst": "abc"}}}}
        save_manifest(manifest, tmp_path)

        loaded = load_manifest(tmp_path)
        assert loaded["folders"]["guides"]["doc_hashes"]["a.rst"] == "abc"
        assert "updated" in loaded

    def test_index_dir_created(self, tmp_path):
        manifest = {"version": "1.0", "folders": {}}
        save_manifest(manifest, tmp_path)
        assert (tmp_path / ".doc-index").is_dir()
        assert (tmp_path / ".doc-index" / "manifest.json").exists()


# ── folder_needs_reindex ─────────────────────────────────────────────────────


class TestFolderNeedsReindex:
    def test_new_folder_needs_reindex(self, doc_tree):
        manifest = {"folders": {}}
        assert folder_needs_reindex("guides/operations", manifest, doc_tree) is True

    def test_unchanged_folder_no_reindex(self, doc_tree):
        hashes = get_folder_doc_hashes("guides/operations", doc_tree)
        manifest = {"folders": {"guides/operations": {"doc_hashes": hashes}}}
        index_dir = doc_tree / ".doc-index"
        index_dir.mkdir(exist_ok=True)
        index_file = index_dir / "guides-operations.index.md"
        index_file.write_text("# Index for guides/operations")

        with patch("doc_index.get_folder_doc_hashes_from_ref", return_value=None):
            assert folder_needs_reindex("guides/operations", manifest, doc_tree) is False

    def test_changed_file_needs_reindex(self, doc_tree):
        hashes = get_folder_doc_hashes("guides/operations", doc_tree)
        manifest = {"folders": {"guides/operations": {"doc_hashes": hashes}}}
        index_dir = doc_tree / ".doc-index"
        index_dir.mkdir(exist_ok=True)
        index_file = index_dir / "guides-operations.index.md"
        index_file.write_text("# Index for guides/operations")

        (doc_tree / "guides" / "operations" / "health-checks.rst").write_text("UPDATED CONTENT")
        with patch("doc_index.get_folder_doc_hashes_from_ref", return_value=None):
            assert folder_needs_reindex("guides/operations", manifest, doc_tree) is True


# ── save_index / load_index ──────────────────────────────────────────────────


class TestSaveAndLoadIndex:
    def test_save_creates_file(self, tmp_path):
        result = save_index("guides/operations", "# Index content", tmp_path)
        assert result.exists()
        assert result.name == "guides-operations.index.md"

    def test_load_saved_index(self, tmp_path):
        save_index("tutorials", "# Tutorial index", tmp_path)
        content = load_index("tutorials", tmp_path)
        assert content == "# Tutorial index"

    def test_load_missing_index(self, tmp_path):
        assert load_index("nonexistent", tmp_path) is None

    def test_save_root_level(self, tmp_path):
        save_index(ROOT_LEVEL_FOLDER, "# Root index", tmp_path)
        content = load_index(ROOT_LEVEL_FOLDER, tmp_path)
        assert content == "# Root index"


# ── load_all_indexes ─────────────────────────────────────────────────────────


class TestLoadAllIndexes:
    def test_loads_multiple(self, doc_tree):
        save_index("guides/operations", "# Ops index", doc_tree)
        save_index("tutorials", "# Tutorial index", doc_tree)

        indexes = load_all_indexes(doc_tree)
        assert "guides/operations" in indexes
        assert "tutorials" in indexes
        assert indexes["guides/operations"] == "# Ops index"

    def test_empty_no_index_dir(self, tmp_path):
        indexes = load_all_indexes(tmp_path)
        assert indexes == {}

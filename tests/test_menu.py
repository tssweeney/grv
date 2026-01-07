from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gtwsp.menu import (
    _status_indicators,
    build_menu_entries,
    interactive_select,
)
from gtwsp.status import BranchStatus


class TestStatusIndicators:
    def test_merged(self) -> None:
        branch = BranchStatus(
            name="f",
            path=Path("/"),
            has_remote=True,
            is_merged=True,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        assert "merged" in _status_indicators(branch)

    def test_unpushed(self) -> None:
        branch = BranchStatus(
            name="f",
            path=Path("/"),
            has_remote=True,
            is_merged=False,
            unpushed_commits=3,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        assert "+3" in _status_indicators(branch)

    def test_uncommitted(self) -> None:
        branch = BranchStatus(
            name="f",
            path=Path("/"),
            has_remote=True,
            is_merged=False,
            unpushed_commits=0,
            uncommitted_changes=5,
            insertions=3,
            deletions=2,
        )
        assert "~5" in _status_indicators(branch)

    def test_no_remote(self) -> None:
        branch = BranchStatus(
            name="f",
            path=Path("/"),
            has_remote=False,
            is_merged=False,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        assert "no remote" in _status_indicators(branch)

    def test_clean(self) -> None:
        branch = BranchStatus(
            name="f",
            path=Path("/"),
            has_remote=True,
            is_merged=False,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        assert _status_indicators(branch) == []


class TestBuildMenuEntries:
    def test_builds_entries(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITWSP_ROOT", str(tmp_path))
        branch = BranchStatus(
            name="main",
            path=tmp_path / "main",
            has_remote=True,
            is_merged=True,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        with (
            patch("gtwsp.menu.get_all_repos", return_value=[("repo", tmp_path)]),
            patch("gtwsp.menu.get_repo_branches", return_value=[branch]),
        ):
            entries = build_menu_entries()
            assert len(entries) == 1
            assert "repo/main" in entries[0][0]
            assert entries[0][1] == branch

    def test_empty_repos(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITWSP_ROOT", str(tmp_path))
        with patch("gtwsp.menu.get_all_repos", return_value=[]):
            entries = build_menu_entries()
            assert entries == []


class TestInteractiveSelect:
    def test_returns_none_when_no_entries(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITWSP_ROOT", str(tmp_path))
        with patch("gtwsp.menu.build_menu_entries", return_value=[]):
            result = interactive_select()
            assert result is None

    def test_returns_selected_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITWSP_ROOT", str(tmp_path))
        branch = BranchStatus(
            name="main",
            path=tmp_path / "main",
            has_remote=True,
            is_merged=False,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        with (
            patch(
                "gtwsp.menu.build_menu_entries", return_value=[("repo/main", branch)]
            ),
            patch("gtwsp.menu.TerminalMenu") as mock_menu_class,
        ):
            mock_menu = MagicMock()
            mock_menu.show.return_value = 0
            mock_menu_class.return_value = mock_menu
            result = interactive_select()
            assert result == tmp_path / "main"

    def test_returns_none_when_cancelled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITWSP_ROOT", str(tmp_path))
        branch = BranchStatus(
            name="main",
            path=tmp_path / "main",
            has_remote=True,
            is_merged=False,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        with (
            patch(
                "gtwsp.menu.build_menu_entries", return_value=[("repo/main", branch)]
            ),
            patch("gtwsp.menu.TerminalMenu") as mock_menu_class,
        ):
            mock_menu = MagicMock()
            mock_menu.show.return_value = None  # User pressed q
            mock_menu_class.return_value = mock_menu
            result = interactive_select()
            assert result is None

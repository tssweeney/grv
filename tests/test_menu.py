from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from grove.menu import (
    build_menu_entries,
    interactive_select,
)
from grove.status import BranchInfo


class TestBuildMenuEntries:
    def test_builds_entries(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GROVE_ROOT", str(tmp_path))
        branch = BranchInfo(name="main", path=tmp_path / "main")
        with (
            patch("grove.menu.get_all_repos", return_value=[("repo", tmp_path)]),
            patch("grove.menu.get_repo_branches_fast", return_value=[branch]),
        ):
            entries = build_menu_entries()
            assert len(entries) == 1
            assert entries[0][0] == "repo/main"
            assert entries[0][1] == branch

    def test_empty_repos(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GROVE_ROOT", str(tmp_path))
        with patch("grove.menu.get_all_repos", return_value=[]):
            entries = build_menu_entries()
            assert entries == []


class TestInteractiveSelect:
    def test_returns_none_when_no_entries(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GROVE_ROOT", str(tmp_path))
        with patch("grove.menu.build_menu_entries", return_value=[]):
            result = interactive_select()
            assert result is None

    def test_returns_selected_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GROVE_ROOT", str(tmp_path))
        branch = BranchInfo(name="main", path=tmp_path / "main")
        with (
            patch(
                "grove.menu.build_menu_entries", return_value=[("repo/main", branch)]
            ),
            patch("grove.menu.TerminalMenu") as mock_menu_class,
        ):
            mock_menu = MagicMock()
            mock_menu.show.return_value = 0
            mock_menu_class.return_value = mock_menu
            result = interactive_select()
            assert result == tmp_path / "main"

    def test_returns_none_when_cancelled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GROVE_ROOT", str(tmp_path))
        branch = BranchInfo(name="main", path=tmp_path / "main")
        with (
            patch(
                "grove.menu.build_menu_entries", return_value=[("repo/main", branch)]
            ),
            patch("grove.menu.TerminalMenu") as mock_menu_class,
        ):
            mock_menu = MagicMock()
            mock_menu.show.return_value = None  # User pressed q
            mock_menu_class.return_value = mock_menu
            result = interactive_select()
            assert result is None

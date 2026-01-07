from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from gtwsp.cli import _build_status_parts, _get_cleanable_branches, main
from gtwsp.status import BranchStatus


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestMain:
    def test_no_command_shows_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main)
        assert result.exit_code == 0
        assert "Manage git worktrees" in result.output

    def test_help_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "shell" in result.output


class TestShell:
    def test_shell_creates_worktree(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITWSP_ROOT", str(tmp_path))
        with (
            patch("gtwsp.cli.ensure_base_repo"),
            patch("gtwsp.cli.ensure_worktree"),
            patch("gtwsp.cli.get_default_branch", return_value="main"),
            patch("os.chdir"),
            patch("os.execvp"),
        ):
            tree_path = (
                tmp_path / "repos" / "github_com_user_repo" / "tree_branches" / "main"
            )
            tree_path.mkdir(parents=True)
            result = runner.invoke(main, ["shell", "https://github.com/user/repo.git"])
            assert "Branch: main" in result.output

    def test_shell_with_branch(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITWSP_ROOT", str(tmp_path))
        with (
            patch("gtwsp.cli.ensure_base_repo"),
            patch("gtwsp.cli.ensure_worktree"),
            patch("os.chdir"),
            patch("os.execvp"),
        ):
            tree_path = (
                tmp_path
                / "repos"
                / "github_com_user_repo"
                / "tree_branches"
                / "feature"
            )
            tree_path.mkdir(parents=True)
            result = runner.invoke(
                main, ["shell", "https://github.com/user/repo.git", "feature"]
            )
            assert "Branch: feature" in result.output


class TestList:
    def test_list_no_repos(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITWSP_ROOT", str(tmp_path))
        result = runner.invoke(main, ["list", "--no-interactive"])
        assert "No repositories found" in result.output

    def test_list_with_repos(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITWSP_ROOT", str(tmp_path))
        with patch("gtwsp.cli.get_all_repos") as mock_repos:
            mock_repos.return_value = [("github_com_user_repo", tmp_path)]
            with patch("gtwsp.cli.get_repo_branches") as mock_branches:
                mock_branches.return_value = [
                    BranchStatus(
                        name="main",
                        path=tmp_path / "main",
                        has_remote=True,
                        is_merged=True,
                        unpushed_commits=0,
                        uncommitted_changes=0,
                        insertions=0,
                        deletions=0,
                    )
                ]
                result = runner.invoke(main, ["list", "-n"])
                assert "github_com_user_repo" in result.output
                assert "main" in result.output

    def test_list_skips_empty_repos(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITWSP_ROOT", str(tmp_path))
        with patch("gtwsp.cli.get_all_repos") as mock_repos:
            mock_repos.return_value = [("empty_repo", tmp_path)]
            with patch("gtwsp.cli.get_repo_branches", return_value=[]):
                result = runner.invoke(main, ["list", "-n"])
                assert "empty_repo" not in result.output

    def test_list_interactive_selects_branch(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITWSP_ROOT", str(tmp_path))
        with (
            patch("gtwsp.cli.get_all_repos", return_value=[("repo", tmp_path)]),
            patch("gtwsp.menu.interactive_select", return_value=tmp_path / "main"),
            patch("gtwsp.menu.shell_into") as mock_shell,
        ):
            runner.invoke(main, ["list"])
            mock_shell.assert_called_once_with(tmp_path / "main")

    def test_list_interactive_cancelled(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITWSP_ROOT", str(tmp_path))
        with (
            patch("gtwsp.cli.get_all_repos", return_value=[("repo", tmp_path)]),
            patch("gtwsp.menu.interactive_select", return_value=None),
            patch("gtwsp.menu.shell_into") as mock_shell,
        ):
            runner.invoke(main, ["list"])
            mock_shell.assert_not_called()


class TestClean:
    def test_clean_nothing_to_clean(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITWSP_ROOT", str(tmp_path))
        with patch("gtwsp.cli._get_cleanable_branches", return_value=[]):
            result = runner.invoke(main, ["clean"])
            assert "Nothing to clean" in result.output

    def test_clean_dry_run(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITWSP_ROOT", str(tmp_path))
        branch = BranchStatus(
            name="feature",
            path=tmp_path / "feature",
            has_remote=True,
            is_merged=True,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        with patch("gtwsp.cli._get_cleanable_branches", return_value=[branch]):
            result = runner.invoke(main, ["clean", "--dry-run"])
            assert "Would remove 1 worktree" in result.output

    def test_clean_with_force(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITWSP_ROOT", str(tmp_path))
        repo_path = tmp_path / "repo"
        trunk = repo_path / "trunk"
        trunk.mkdir(parents=True)
        branch_path = repo_path / "tree_branches" / "feature"
        branch = BranchStatus(
            name="feature",
            path=branch_path,
            has_remote=True,
            is_merged=True,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        with (
            patch("gtwsp.cli._get_cleanable_branches", return_value=[branch]),
            patch("subprocess.run"),
        ):
            result = runner.invoke(main, ["clean", "--force"])
            assert "Cleaned 1 worktree" in result.output

    def test_clean_abort(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITWSP_ROOT", str(tmp_path))
        branch = BranchStatus(
            name="feature",
            path=tmp_path / "feature",
            has_remote=True,
            is_merged=True,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        with patch("gtwsp.cli._get_cleanable_branches", return_value=[branch]):
            result = runner.invoke(main, ["clean"], input="n\n")
            assert result.exit_code == 1


class TestBuildStatusParts:
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
        parts = _build_status_parts(branch)
        assert any("merged" in p for p in parts)

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
        parts = _build_status_parts(branch)
        assert any("unpushed" in p for p in parts)

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
        parts = _build_status_parts(branch)
        assert any("~5" in p for p in parts)

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
        parts = _build_status_parts(branch)
        assert any("no remote" in p for p in parts)


class TestGetCleanableBranches:
    def test_filters_safe_branches(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITWSP_ROOT", str(tmp_path))
        safe = BranchStatus(
            name="safe",
            path=Path("/safe"),
            has_remote=True,
            is_merged=True,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        unsafe = BranchStatus(
            name="unsafe",
            path=Path("/unsafe"),
            has_remote=False,
            is_merged=True,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        with (
            patch("gtwsp.cli.get_all_repos", return_value=[("repo", tmp_path)]),
            patch("gtwsp.cli.get_repo_branches", return_value=[safe, unsafe]),
        ):
            result = _get_cleanable_branches()
            assert len(result) == 1
            assert result[0].name == "safe"

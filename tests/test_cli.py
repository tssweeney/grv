from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from grv.cli import main
from grv.menu import MenuAction
from grv.status import BranchInfo, BranchStatus


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
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        with (
            patch("grv.cli.ensure_base_repo"),
            patch("grv.cli.ensure_worktree"),
            patch("grv.cli.get_default_branch", return_value="main"),
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
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        with (
            patch("grv.cli.ensure_base_repo"),
            patch("grv.cli.ensure_worktree"),
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

    def test_shell_with_from_branch(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        with (
            patch("grv.cli.ensure_base_repo"),
            patch("grv.cli.ensure_worktree") as mock_ensure_worktree,
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
                main,
                [
                    "shell",
                    "https://github.com/user/repo.git",
                    "feature",
                    "--from",
                    "develop",
                ],
            )
            assert "Branch: feature" in result.output
            mock_ensure_worktree.assert_called_once()
            call_kwargs = mock_ensure_worktree.call_args
            assert call_kwargs.kwargs.get("from_branch") == "develop"

    def test_shell_with_gh_shorthand_from_branch(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test gh: shorthand with @from_branch extracts and uses the base branch."""
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        with (
            patch("grv.cli.ensure_base_repo") as mock_ensure_base,
            patch("grv.cli.ensure_worktree") as mock_ensure_worktree,
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
                main,
                ["shell", "gh:user/repo@develop", "feature"],
            )
            assert "Branch: feature" in result.output
            # Verify the URL was expanded
            mock_ensure_base.assert_called_once()
            base_call_args = mock_ensure_base.call_args[0]
            assert base_call_args[0] == "git@github.com:user/repo.git"
            # Verify from_branch was extracted from shorthand
            mock_ensure_worktree.assert_called_once()
            worktree_call_kwargs = mock_ensure_worktree.call_args
            assert worktree_call_kwargs.kwargs.get("from_branch") == "develop"


class TestList:
    def test_list_no_repos(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        result = runner.invoke(main, ["list"])
        assert "No repositories found" in result.output

    def test_list_selects_branch(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        with (
            patch("grv.cli.get_all_repos", return_value=[("repo", tmp_path)]),
            patch(
                "grv.menu.interactive_select",
                return_value=(tmp_path / "main", "main", MenuAction.SHELL),
            ),
            patch("grv.menu.shell_into") as mock_shell,
        ):
            runner.invoke(main, ["list"])
            mock_shell.assert_called_once_with(tmp_path / "main", "main")

    def test_list_cancelled(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        with (
            patch("grv.cli.get_all_repos", return_value=[("repo", tmp_path)]),
            patch("grv.menu.interactive_select", return_value=None),
            patch("grv.menu.shell_into") as mock_shell,
        ):
            runner.invoke(main, ["list"])
            mock_shell.assert_not_called()

    def test_list_clean_action_safe_removes_empty_repo(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        repo_path = tmp_path / "repo"
        branch_path = repo_path / "tree_branches" / "feature"
        branch_path.mkdir(parents=True)
        (repo_path / "trunk").mkdir(parents=True)
        safe_status = BranchStatus(
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
            patch("grv.cli.get_all_repos", return_value=[("repo", repo_path)]),
            patch(
                "grv.menu.interactive_select",
                return_value=(branch_path, "feature", MenuAction.CLEAN),
            ),
            patch("grv.cli.get_branch_status", return_value=safe_status),
            patch("grv.cli.get_repo_branches_fast", return_value=[]),
            patch("subprocess.run"),
        ):
            result = runner.invoke(main, ["list"])
            assert "Cleaning 'feature'" in result.output
            assert "Removing empty repo" in result.output
            assert "Done" in result.output

    def test_list_clean_action_safe_keeps_nonempty_repo(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        repo_path = tmp_path / "repo"
        branch_path = repo_path / "tree_branches" / "feature"
        branch_path.mkdir(parents=True)
        (repo_path / "trunk").mkdir(parents=True)
        safe_status = BranchStatus(
            name="feature",
            path=branch_path,
            has_remote=True,
            is_merged=True,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        other_path = repo_path / "tree_branches" / "other"
        other_branch = BranchInfo(name="other", path=other_path)
        with (
            patch("grv.cli.get_all_repos", return_value=[("repo", repo_path)]),
            patch(
                "grv.menu.interactive_select",
                return_value=(branch_path, "feature", MenuAction.CLEAN),
            ),
            patch("grv.cli.get_branch_status", return_value=safe_status),
            patch("grv.cli.get_repo_branches_fast", return_value=[other_branch]),
            patch("subprocess.run"),
        ):
            result = runner.invoke(main, ["list"])
            assert "Cleaning 'feature'" in result.output
            assert "Removing empty repo" not in result.output
            assert "Done" in result.output

    def test_list_clean_action_unsafe_no_remote(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        repo_path = tmp_path / "repo"
        branch_path = repo_path / "tree_branches" / "feature"
        branch_path.mkdir(parents=True)
        (repo_path / "trunk").mkdir(parents=True)
        unsafe_status = BranchStatus(
            name="feature",
            path=branch_path,
            has_remote=False,
            is_merged=False,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        with (
            patch("grv.cli.get_all_repos", return_value=[("repo", repo_path)]),
            patch(
                "grv.menu.interactive_select",
                return_value=(branch_path, "feature", MenuAction.CLEAN),
            ),
            patch("grv.cli.get_branch_status", return_value=unsafe_status),
        ):
            result = runner.invoke(main, ["list"])
            assert "Cannot clean 'feature'" in result.output
            assert "No remote branch found" in result.output

    def test_list_clean_action_unsafe_unpushed(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        repo_path = tmp_path / "repo"
        branch_path = repo_path / "tree_branches" / "feature"
        branch_path.mkdir(parents=True)
        (repo_path / "trunk").mkdir(parents=True)
        unsafe_status = BranchStatus(
            name="feature",
            path=branch_path,
            has_remote=True,
            is_merged=False,
            unpushed_commits=2,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        with (
            patch("grv.cli.get_all_repos", return_value=[("repo", repo_path)]),
            patch(
                "grv.menu.interactive_select",
                return_value=(branch_path, "feature", MenuAction.CLEAN),
            ),
            patch("grv.cli.get_branch_status", return_value=unsafe_status),
        ):
            result = runner.invoke(main, ["list"])
            assert "Cannot clean 'feature'" in result.output
            assert "2 unpushed commit(s)" in result.output

    def test_list_clean_action_unsafe_uncommitted(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        repo_path = tmp_path / "repo"
        branch_path = repo_path / "tree_branches" / "feature"
        branch_path.mkdir(parents=True)
        (repo_path / "trunk").mkdir(parents=True)
        unsafe_status = BranchStatus(
            name="feature",
            path=branch_path,
            has_remote=True,
            is_merged=False,
            unpushed_commits=0,
            uncommitted_changes=5,
            insertions=3,
            deletions=2,
        )
        with (
            patch("grv.cli.get_all_repos", return_value=[("repo", repo_path)]),
            patch(
                "grv.menu.interactive_select",
                return_value=(branch_path, "feature", MenuAction.CLEAN),
            ),
            patch("grv.cli.get_branch_status", return_value=unsafe_status),
        ):
            result = runner.invoke(main, ["list"])
            assert "Cannot clean 'feature'" in result.output
            assert "5 uncommitted changes" in result.output

    def test_list_delete_action_confirmed(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        repo_path = tmp_path / "repo"
        branch_path = repo_path / "tree_branches" / "feature"
        branch_path.mkdir(parents=True)
        (repo_path / "trunk").mkdir(parents=True)
        unsafe_status = BranchStatus(
            name="feature",
            path=branch_path,
            has_remote=False,
            is_merged=False,
            unpushed_commits=1,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        with (
            patch("grv.cli.get_all_repos", return_value=[("repo", repo_path)]),
            patch(
                "grv.menu.interactive_select",
                return_value=(branch_path, "feature", MenuAction.DELETE),
            ),
            patch("grv.cli.get_branch_status", return_value=unsafe_status),
            patch("grv.cli.get_repo_branches_fast", return_value=[]),
            patch("subprocess.run"),
        ):
            result = runner.invoke(main, ["list"], input="y\n")
            assert "Force deleting 'feature'" in result.output
            assert "Done" in result.output

    def test_list_delete_action_declined(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        repo_path = tmp_path / "repo"
        branch_path = repo_path / "tree_branches" / "feature"
        with (
            patch("grv.cli.get_all_repos", return_value=[("repo", repo_path)]),
            patch(
                "grv.menu.interactive_select",
                return_value=(branch_path, "feature", MenuAction.DELETE),
            ),
        ):
            result = runner.invoke(main, ["list"], input="n\n")
            assert "Force deleting" not in result.output


class TestClean:
    def test_clean_no_repos(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        result = runner.invoke(main, ["clean"])
        assert "No repositories to scan" in result.output

    def test_clean_no_branches(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        with (
            patch("grv.cli.get_all_repos", return_value=[("repo", tmp_path)]),
            patch("grv.cli.get_repo_branches_fast", return_value=[]),
        ):
            result = runner.invoke(main, ["clean"])
            assert "No branches to scan" in result.output

    def test_clean_nothing_to_clean(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        branch_info = BranchInfo(name="feature", path=tmp_path / "feature")
        unsafe_status = BranchStatus(
            name="feature",
            path=tmp_path / "feature",
            has_remote=False,
            is_merged=False,
            unpushed_commits=1,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        with (
            patch("grv.cli.get_all_repos", return_value=[("repo", tmp_path)]),
            patch("grv.cli.get_repo_branches_fast", return_value=[branch_info]),
            patch("grv.cli.get_branch_status", return_value=unsafe_status),
        ):
            result = runner.invoke(main, ["clean"])
            assert "Nothing to clean" in result.output

    def test_clean_dry_run(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        branch_info = BranchInfo(name="feature", path=tmp_path / "feature")
        safe_status = BranchStatus(
            name="feature",
            path=tmp_path / "feature",
            has_remote=True,
            is_merged=True,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        with (
            patch("grv.cli.get_all_repos", return_value=[("repo", tmp_path)]),
            patch("grv.cli.get_repo_branches_fast", return_value=[branch_info]),
            patch("grv.cli.get_branch_status", return_value=safe_status),
        ):
            result = runner.invoke(main, ["clean", "--dry-run"])
            assert "Would remove 1 worktree" in result.output

    def test_clean_with_force(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        repo_path = tmp_path / "repo"
        trunk = repo_path / "trunk"
        trunk.mkdir(parents=True)
        branch_path = repo_path / "tree_branches" / "feature"
        branch_info = BranchInfo(name="feature", path=branch_path)
        safe_status = BranchStatus(
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
            patch("grv.cli.get_all_repos", return_value=[("repo", repo_path)]),
            patch("grv.cli.get_repo_branches_fast", return_value=[branch_info]),
            patch("grv.cli.get_branch_status", return_value=safe_status),
            patch("subprocess.run"),
        ):
            result = runner.invoke(main, ["clean", "--force"])
            assert "Cleaned 1 worktree" in result.output

    def test_clean_abort(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        branch_info = BranchInfo(name="feature", path=tmp_path / "feature")
        safe_status = BranchStatus(
            name="feature",
            path=tmp_path / "feature",
            has_remote=True,
            is_merged=True,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        with (
            patch("grv.cli.get_all_repos", return_value=[("repo", tmp_path)]),
            patch("grv.cli.get_repo_branches_fast", return_value=[branch_info]),
            patch("grv.cli.get_branch_status", return_value=safe_status),
        ):
            result = runner.invoke(main, ["clean"], input="n\n")
            assert result.exit_code == 1

    def test_clean_filters_unsafe_branches(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        clean_info = BranchInfo(name="cleanable", path=tmp_path / "cleanable")
        dirty_info = BranchInfo(name="dirty", path=tmp_path / "dirty")
        clean_status = BranchStatus(
            name="cleanable",
            path=tmp_path / "cleanable",
            has_remote=True,
            is_merged=True,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        dirty_status = BranchStatus(
            name="dirty",
            path=tmp_path / "dirty",
            has_remote=False,
            is_merged=False,  # Not merged, so NOT safe to clean
            unpushed_commits=2,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )

        def mock_status(_path: Path, _trunk: Path, name: str) -> BranchStatus:
            return clean_status if name == "cleanable" else dirty_status

        with (
            patch("grv.cli.get_all_repos", return_value=[("repo", tmp_path)]),
            patch(
                "grv.cli.get_repo_branches_fast",
                return_value=[clean_info, dirty_info],
            ),
            patch("grv.cli.get_branch_status", side_effect=mock_status),
        ):
            result = runner.invoke(main, ["clean", "--dry-run"])
            assert "cleanable" in result.output
            assert "dirty" not in result.output
            assert "Would remove 1 worktree" in result.output

    def test_clean_removes_empty_repo(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRV_ROOT", str(tmp_path))
        repo_path = tmp_path / "repo"
        trunk = repo_path / "trunk"
        trunk.mkdir(parents=True)
        branch_path = repo_path / "tree_branches" / "feature"
        branch_path.mkdir(parents=True)
        branch_info = BranchInfo(name="feature", path=branch_path)
        safe_status = BranchStatus(
            name="feature",
            path=branch_path,
            has_remote=True,
            is_merged=True,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        call_count = [0]

        def mock_branches_fast(_path: Path) -> list[BranchInfo]:
            call_count[0] += 1
            return [branch_info] if call_count[0] == 1 else []

        with (
            patch("grv.cli.get_all_repos", return_value=[("repo", repo_path)]),
            patch("grv.cli.get_repo_branches_fast", side_effect=mock_branches_fast),
            patch("grv.cli.get_branch_status", return_value=safe_status),
            patch("subprocess.run"),
        ):
            result = runner.invoke(main, ["clean", "--force"])
            assert "Cleaned 1 worktree" in result.output
            assert "1 empty repo" in result.output
            assert not repo_path.exists()

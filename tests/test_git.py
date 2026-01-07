from pathlib import Path
from unittest.mock import MagicMock, patch

from grove.git import (
    branch_exists_locally,
    ensure_base_repo,
    ensure_worktree,
    get_default_branch,
    run_git,
)


class TestRunGit:
    def test_run_git_capture(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="output", returncode=0)
            run_git("status", cwd=tmp_path, capture=True)
            assert mock_run.called

    def test_run_git_no_capture(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            run_git("status", cwd=tmp_path, capture=False)
            assert mock_run.called


class TestGetDefaultBranch:
    def test_get_default_branch(self, tmp_path: Path) -> None:
        with patch("grove.git.run_git") as mock:
            mock.return_value = MagicMock(
                stdout="refs/remotes/origin/main\n", returncode=0
            )
            result = get_default_branch(tmp_path)
            assert result == "main"

    def test_get_default_branch_master(self, tmp_path: Path) -> None:
        with patch("grove.git.run_git") as mock:
            mock.return_value = MagicMock(
                stdout="refs/remotes/origin/master\n", returncode=0
            )
            result = get_default_branch(tmp_path)
            assert result == "master"


class TestBranchExistsLocally:
    def test_branch_exists(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock:
            mock.return_value = MagicMock(returncode=0)
            assert branch_exists_locally(tmp_path, "main") is True

    def test_branch_not_exists(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock:
            mock.return_value = MagicMock(returncode=1)
            assert branch_exists_locally(tmp_path, "nonexistent") is False


class TestEnsureBaseRepo:
    def test_clone_new_repo(self, tmp_path: Path) -> None:
        base_path = tmp_path / "repo"
        with patch("grove.git.run_git") as mock_git:
            mock_git.return_value = MagicMock(
                stdout="refs/remotes/origin/main\n", returncode=0
            )
            ensure_base_repo("https://github.com/user/repo.git", base_path)
            calls = [str(c) for c in mock_git.call_args_list]
            assert any("clone" in c for c in calls)

    def test_update_existing_repo(self, tmp_path: Path) -> None:
        base_path = tmp_path / "repo"
        base_path.mkdir()
        with patch("grove.git.run_git") as mock_git:
            mock_git.return_value = MagicMock(
                stdout="refs/remotes/origin/main\n", returncode=0
            )
            ensure_base_repo("https://github.com/user/repo.git", base_path)
            calls = [str(c) for c in mock_git.call_args_list]
            assert any("fetch" in c for c in calls)


class TestEnsureWorktree:
    def test_worktree_exists(self, tmp_path: Path) -> None:
        tree_path = tmp_path / "tree"
        tree_path.mkdir()
        with patch("grove.git.run_git") as mock_git:
            ensure_worktree(tmp_path, tree_path, "feature")
            mock_git.assert_not_called()

    def test_create_worktree_local_branch(self, tmp_path: Path) -> None:
        base_path = tmp_path / "base"
        base_path.mkdir()
        tree_path = tmp_path / "tree"
        with (
            patch("grove.git.branch_exists_locally", return_value=True),
            patch("grove.git.run_git") as mock_git,
        ):
            ensure_worktree(base_path, tree_path, "feature")
            calls = [str(c) for c in mock_git.call_args_list]
            assert any("worktree" in c for c in calls)

    def test_create_worktree_remote_branch(self, tmp_path: Path) -> None:
        base_path = tmp_path / "base"
        base_path.mkdir()
        tree_path = tmp_path / "tree"
        with (
            patch("grove.git.branch_exists_locally", return_value=False),
            patch("grove.git.run_git") as mock_git,
        ):
            mock_git.return_value = MagicMock(
                stdout="abc123 refs/heads/feature\n", returncode=0
            )
            ensure_worktree(base_path, tree_path, "feature")

    def test_create_worktree_new_branch(self, tmp_path: Path) -> None:
        base_path = tmp_path / "base"
        base_path.mkdir()
        tree_path = tmp_path / "tree"
        with (
            patch("grove.git.branch_exists_locally", return_value=False),
            patch("grove.git.run_git") as mock_git,
            patch("grove.git.get_default_branch", return_value="main"),
        ):
            mock_git.return_value = MagicMock(stdout="", returncode=0)
            ensure_worktree(base_path, tree_path, "new-feature")

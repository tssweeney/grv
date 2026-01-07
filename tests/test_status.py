from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from grove.status import (
    BranchInfo,
    BranchStatus,
    get_all_repos,
    get_branch_status,
    get_repo_branches,
    get_repo_branches_fast,
)


class TestBranchStatus:
    def test_is_safe_to_clean_true(self) -> None:
        status = BranchStatus(
            name="feature",
            path=Path("/tmp/feature"),
            has_remote=True,
            is_merged=True,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        assert status.is_safe_to_clean is True

    def test_is_safe_to_clean_no_remote(self) -> None:
        status = BranchStatus(
            name="feature",
            path=Path("/tmp/feature"),
            has_remote=False,
            is_merged=True,
            unpushed_commits=0,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        assert status.is_safe_to_clean is False

    def test_is_safe_to_clean_unpushed(self) -> None:
        status = BranchStatus(
            name="feature",
            path=Path("/tmp/feature"),
            has_remote=True,
            is_merged=False,
            unpushed_commits=1,
            uncommitted_changes=0,
            insertions=0,
            deletions=0,
        )
        assert status.is_safe_to_clean is False

    def test_is_safe_to_clean_uncommitted(self) -> None:
        status = BranchStatus(
            name="feature",
            path=Path("/tmp/feature"),
            has_remote=True,
            is_merged=False,
            unpushed_commits=0,
            uncommitted_changes=5,
            insertions=3,
            deletions=2,
        )
        assert status.is_safe_to_clean is False


class TestGetBranchStatus:
    def test_with_remote_and_merged(self, tmp_path: Path) -> None:
        def mock_run(cmd: list[str], **_kw: object) -> MagicMock:
            if "ls-remote" in cmd:
                return MagicMock(stdout="abc123 refs/heads/feature\n", returncode=0)
            if "branch" in cmd and "--merged" in cmd:
                return MagicMock(stdout="  feature\n  main\n", returncode=0)
            if "rev-list" in cmd:
                return MagicMock(stdout="0\n", returncode=0)
            if "diff" in cmd:
                return MagicMock(stdout="", returncode=0)
            return MagicMock(stdout="", returncode=0)

        with (
            patch("subprocess.run", side_effect=mock_run),
            patch("grove.status.get_default_branch", return_value="main"),
        ):
            status = get_branch_status(tmp_path, tmp_path, "feature")
            assert status.has_remote is True
            assert status.is_merged is True
            assert status.unpushed_commits == 0

    def test_no_remote(self, tmp_path: Path) -> None:
        def mock_run(cmd: list[str], **_kw: object) -> MagicMock:
            if "ls-remote" in cmd:
                return MagicMock(stdout="", returncode=0)
            if "branch" in cmd:
                return MagicMock(stdout="", returncode=0)
            if "rev-list" in cmd:
                return MagicMock(stdout="2\n", returncode=0)
            if "diff" in cmd:
                return MagicMock(stdout="", returncode=0)
            return MagicMock(stdout="", returncode=0)

        with (
            patch("subprocess.run", side_effect=mock_run),
            patch("grove.status.get_default_branch", return_value="main"),
        ):
            status = get_branch_status(tmp_path, tmp_path, "feature")
            assert status.has_remote is False
            assert status.unpushed_commits == 2

    def test_with_uncommitted_changes(self, tmp_path: Path) -> None:
        def mock_run(cmd: list[str], **_kw: object) -> MagicMock:
            if "ls-remote" in cmd:
                return MagicMock(stdout="abc refs/heads/f\n", returncode=0)
            if "branch" in cmd:
                return MagicMock(stdout="", returncode=0)
            if "rev-list" in cmd:
                return MagicMock(stdout="0\n", returncode=0)
            if "diff" in cmd:
                diff_out = " f.py | 5 ++---\n 1 file, 2 insertions(+), 3 deletions(-)\n"
                return MagicMock(stdout=diff_out, returncode=0)
            return MagicMock(stdout="", returncode=0)

        with (
            patch("subprocess.run", side_effect=mock_run),
            patch("grove.status.get_default_branch", return_value="main"),
        ):
            status = get_branch_status(tmp_path, tmp_path, "feature")
            assert status.insertions == 2
            assert status.deletions == 3
            assert status.uncommitted_changes == 5

    def test_rev_list_failure(self, tmp_path: Path) -> None:
        def mock_run(cmd: list[str], **_kw: object) -> MagicMock:
            if "ls-remote" in cmd:
                return MagicMock(stdout="abc refs/heads/f\n", returncode=0)
            if "branch" in cmd:
                return MagicMock(stdout="", returncode=0)
            if "rev-list" in cmd:
                return MagicMock(stdout="", returncode=1)
            if "diff" in cmd:
                return MagicMock(stdout="", returncode=0)
            return MagicMock(stdout="", returncode=0)

        with (
            patch("subprocess.run", side_effect=mock_run),
            patch("grove.status.get_default_branch", return_value="main"),
        ):
            status = get_branch_status(tmp_path, tmp_path, "feature")
            assert status.unpushed_commits == 0


class TestGetAllRepos:
    def test_no_repos_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GROVE_ROOT", str(tmp_path))
        result = get_all_repos()
        assert result == []

    def test_empty_repos_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GROVE_ROOT", str(tmp_path))
        (tmp_path / "repos").mkdir()
        result = get_all_repos()
        assert result == []

    def test_with_repos(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GROVE_ROOT", str(tmp_path))
        repo_dir = tmp_path / "repos" / "github_com_user_repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "trunk").mkdir()
        result = get_all_repos()
        assert len(result) == 1
        assert result[0][0] == "github_com_user_repo"


class TestGetRepoBranches:
    def test_no_tree_branches(self, tmp_path: Path) -> None:
        result = get_repo_branches(tmp_path)
        assert result == []

    def test_with_branches(self, tmp_path: Path) -> None:
        trunk = tmp_path / "trunk"
        trunk.mkdir()
        branches_dir = tmp_path / "tree_branches"
        branch = branches_dir / "feature"
        branch.mkdir(parents=True)
        (branch / ".git").touch()

        with patch("grove.status.get_branch_status") as mock_status:
            mock_status.return_value = BranchStatus(
                name="feature",
                path=branch,
                has_remote=True,
                is_merged=False,
                unpushed_commits=0,
                uncommitted_changes=0,
                insertions=0,
                deletions=0,
            )
            result = get_repo_branches(tmp_path)
            assert len(result) == 1
            assert result[0].name == "feature"

    def test_skips_non_git_dirs(self, tmp_path: Path) -> None:
        trunk = tmp_path / "trunk"
        trunk.mkdir()
        branches_dir = tmp_path / "tree_branches"
        branch = branches_dir / "not-a-worktree"
        branch.mkdir(parents=True)
        # No .git file

        result = get_repo_branches(tmp_path)
        assert result == []

    def test_branch_with_slashes(self, tmp_path: Path) -> None:
        trunk = tmp_path / "trunk"
        trunk.mkdir()
        branches_dir = tmp_path / "tree_branches"
        # Branch name "feature/foo" creates nested directory
        branch = branches_dir / "feature" / "foo"
        branch.mkdir(parents=True)
        (branch / ".git").touch()

        with patch("grove.status.get_branch_status") as mock_status:
            mock_status.return_value = BranchStatus(
                name="feature/foo",
                path=branch,
                has_remote=True,
                is_merged=False,
                unpushed_commits=0,
                uncommitted_changes=0,
                insertions=0,
                deletions=0,
            )
            result = get_repo_branches(tmp_path)
            assert len(result) == 1
            assert result[0].name == "feature/foo"
            # Verify get_branch_status was called with correct branch name
            mock_status.assert_called_once_with(branch, trunk, "feature/foo")


class TestGetRepoBranchesFast:
    def test_no_tree_branches(self, tmp_path: Path) -> None:
        result = get_repo_branches_fast(tmp_path)
        assert result == []

    def test_with_branches(self, tmp_path: Path) -> None:
        branches_dir = tmp_path / "tree_branches"
        branch = branches_dir / "feature"
        branch.mkdir(parents=True)
        (branch / ".git").touch()

        result = get_repo_branches_fast(tmp_path)
        assert len(result) == 1
        assert result[0].name == "feature"
        assert result[0].path == branch
        assert isinstance(result[0], BranchInfo)

    def test_skips_non_git_dirs(self, tmp_path: Path) -> None:
        branches_dir = tmp_path / "tree_branches"
        branch = branches_dir / "not-a-worktree"
        branch.mkdir(parents=True)
        # No .git file

        result = get_repo_branches_fast(tmp_path)
        assert result == []

    def test_sorts_by_name(self, tmp_path: Path) -> None:
        branches_dir = tmp_path / "tree_branches"
        for name in ["zebra", "alpha", "middle"]:
            branch = branches_dir / name
            branch.mkdir(parents=True)
            (branch / ".git").touch()

        result = get_repo_branches_fast(tmp_path)
        assert [b.name for b in result] == ["alpha", "middle", "zebra"]

    def test_branch_with_slashes(self, tmp_path: Path) -> None:
        branches_dir = tmp_path / "tree_branches"
        # Branch name "feature/foo" creates nested directory
        branch = branches_dir / "feature" / "foo"
        branch.mkdir(parents=True)
        (branch / ".git").touch()

        result = get_repo_branches_fast(tmp_path)
        assert len(result) == 1
        assert result[0].name == "feature/foo"
        assert result[0].path == branch

    def test_mixed_branches_with_and_without_slashes(self, tmp_path: Path) -> None:
        branches_dir = tmp_path / "tree_branches"
        # Simple branch
        simple = branches_dir / "main"
        simple.mkdir(parents=True)
        (simple / ".git").touch()
        # Nested branch
        nested = branches_dir / "feature" / "bar"
        nested.mkdir(parents=True)
        (nested / ".git").touch()

        result = get_repo_branches_fast(tmp_path)
        assert len(result) == 2
        names = [b.name for b in result]
        assert "main" in names
        assert "feature/bar" in names


class TestEdgeCases:
    def test_diff_with_no_summary_line(self, tmp_path: Path) -> None:
        """Test when diff output has no insertion/deletion summary."""

        def mock_run(cmd: list[str], **_kw: object) -> MagicMock:
            if "ls-remote" in cmd:
                return MagicMock(stdout="abc refs/heads/f\n", returncode=0)
            if "branch" in cmd:
                return MagicMock(stdout="", returncode=0)
            if "rev-list" in cmd:
                return MagicMock(stdout="0\n", returncode=0)
            if "diff" in cmd:
                return MagicMock(stdout="file.txt\n", returncode=0)
            return MagicMock(stdout="", returncode=0)

        with (
            patch("subprocess.run", side_effect=mock_run),
            patch("grove.status.get_default_branch", return_value="main"),
        ):
            status = get_branch_status(tmp_path, tmp_path, "feature")
            assert status.uncommitted_changes == 0

    def test_repos_with_file_not_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test repos dir containing a file, not a directory."""
        monkeypatch.setenv("GROVE_ROOT", str(tmp_path))
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir()
        (repos_dir / "not_a_dir").touch()  # File, not a dir

        result = get_all_repos()
        assert result == []

    def test_repos_dir_without_trunk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test repo dir that exists but has no trunk."""
        monkeypatch.setenv("GROVE_ROOT", str(tmp_path))
        repo_dir = tmp_path / "repos" / "incomplete_repo"
        repo_dir.mkdir(parents=True)
        # No trunk subdirectory

        result = get_all_repos()
        assert result == []

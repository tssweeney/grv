import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from grove.config import get_grove_root
from grove.git import get_default_branch


@dataclass
class BranchInfo:
    """Basic branch information (fast, no git operations)."""

    name: str
    path: Path


@dataclass
class BranchStatus:
    """Status information for a worktree branch."""

    name: str
    path: Path
    has_remote: bool
    is_merged: bool
    unpushed_commits: int
    uncommitted_changes: int
    insertions: int
    deletions: int

    @property
    def is_safe_to_clean(self) -> bool:
        """Check if this branch can be safely removed."""
        return (
            self.has_remote
            and self.unpushed_commits == 0
            and self.uncommitted_changes == 0
        )


def get_branch_status(tree_path: Path, trunk_path: Path, branch: str) -> BranchStatus:
    """Get status information for a worktree branch."""
    result = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", branch],
        cwd=trunk_path,
        capture_output=True,
        text=True,
    )
    has_remote = bool(result.stdout.strip())

    default_branch = get_default_branch(trunk_path)
    result = subprocess.run(
        ["git", "branch", "--merged", f"origin/{default_branch}"],
        cwd=tree_path,
        capture_output=True,
        text=True,
    )
    merged = [b.strip().lstrip("* ") for b in result.stdout.strip().split("\n")]
    is_merged = branch in merged

    if has_remote:
        result = subprocess.run(
            ["git", "rev-list", "--count", f"origin/{branch}..{branch}"],
            cwd=tree_path,
            capture_output=True,
            text=True,
        )
        unpushed = int(result.stdout.strip()) if result.returncode == 0 else 0
    else:
        result = subprocess.run(
            ["git", "rev-list", "--count", f"origin/{default_branch}..{branch}"],
            cwd=tree_path,
            capture_output=True,
            text=True,
        )
        unpushed = int(result.stdout.strip()) if result.returncode == 0 else 0

    result = subprocess.run(
        ["git", "diff", "--stat", "HEAD"],
        cwd=tree_path,
        capture_output=True,
        text=True,
    )
    uncommitted, insertions, deletions = 0, 0, 0
    if result.stdout.strip():
        summary = result.stdout.strip().split("\n")[-1]
        if "insertion" in summary or "deletion" in summary:
            ins = re.search(r"(\d+) insertion", summary)
            dels = re.search(r"(\d+) deletion", summary)
            insertions = int(ins.group(1)) if ins else 0
            deletions = int(dels.group(1)) if dels else 0
            uncommitted = insertions + deletions

    return BranchStatus(
        name=branch,
        path=tree_path,
        has_remote=has_remote,
        is_merged=is_merged,
        unpushed_commits=unpushed,
        uncommitted_changes=uncommitted,
        insertions=insertions,
        deletions=deletions,
    )


def get_all_repos() -> list[tuple[str, Path]]:
    """Get all repos in the workspace."""
    repos_dir = get_grove_root() / "repos"
    if not repos_dir.exists():
        return []

    repos = []
    for repo_dir in repos_dir.iterdir():
        if repo_dir.is_dir() and (repo_dir / "trunk").exists():
            repos.append((repo_dir.name, repo_dir))
    return sorted(repos)


def get_repo_branches(repo_path: Path) -> list[BranchStatus]:
    """Get all branches for a repo with their status (slow, uses git)."""
    trunk_path = repo_path / "trunk"
    tree_branches_dir = repo_path / "tree_branches"

    if not tree_branches_dir.exists():
        return []

    branches = []
    for branch_dir in tree_branches_dir.iterdir():
        if branch_dir.is_dir() and (branch_dir / ".git").exists():
            status = get_branch_status(branch_dir, trunk_path, branch_dir.name)
            branches.append(status)

    return sorted(branches, key=lambda b: b.name)


def get_repo_branches_fast(repo_path: Path) -> list[BranchInfo]:
    """Get all branches for a repo (fast, no git operations)."""
    tree_branches_dir = repo_path / "tree_branches"

    if not tree_branches_dir.exists():
        return []

    branches = []
    for branch_dir in tree_branches_dir.iterdir():
        if branch_dir.is_dir() and (branch_dir / ".git").exists():
            branches.append(BranchInfo(name=branch_dir.name, path=branch_dir))

    return sorted(branches, key=lambda b: b.name)

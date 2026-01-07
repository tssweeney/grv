import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import click


def get_gitwsp_root() -> Path:
    """Get the GITWSP_ROOT directory, defaulting to ~/.gitwsp."""
    root = os.environ.get("GITWSP_ROOT", os.path.expanduser("~/.gitwsp"))
    return Path(root)


def extract_repo_name(repo: str) -> str:
    """Extract repository name from a git URL or path."""
    # Handle SSH URLs like git@github.com:user/repo.git
    if repo.startswith("git@"):
        repo = repo.split(":")[-1]

    # Handle HTTPS URLs
    parsed = urlparse(repo)
    if parsed.path:
        repo = parsed.path

    # Remove .git suffix and leading slashes
    repo = repo.rstrip("/").removesuffix(".git")
    repo = repo.lstrip("/")

    # Get just the repo name (last component)
    return repo.split("/")[-1]


def run_git(*args: str, cwd: Path | None = None, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a git command."""
    cmd = ["git", *args]
    if capture:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
    return subprocess.run(cmd, cwd=cwd, check=True)


def get_default_branch(repo_path: Path) -> str:
    """Get the default branch name (main or master)."""
    result = run_git("symbolic-ref", "refs/remotes/origin/HEAD", cwd=repo_path, capture=True)
    # Returns something like "refs/remotes/origin/main"
    return result.stdout.strip().split("/")[-1]


def ensure_base_repo(repo_url: str, base_path: Path) -> None:
    """Ensure the base repository exists and is up to date.

    The base repo is kept with a detached HEAD so all branches
    can be used in worktrees.
    """
    if base_path.exists():
        click.echo(f"Updating base repo at {base_path}...", err=True)
        run_git("fetch", "--all", "--prune", cwd=base_path)
        # Update local tracking branches
        default_branch = get_default_branch(base_path)
        run_git("checkout", "--detach", f"origin/{default_branch}", cwd=base_path)
    else:
        click.echo(f"Cloning base repo to {base_path}...", err=True)
        base_path.parent.mkdir(parents=True, exist_ok=True)
        run_git("clone", repo_url, str(base_path))
        # Detach HEAD so branches can be used in worktrees
        default_branch = get_default_branch(base_path)
        run_git("checkout", "--detach", f"origin/{default_branch}", cwd=base_path)


def branch_exists_locally(base_path: Path, branch: str) -> bool:
    """Check if a branch exists locally."""
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=base_path,
    )
    return result.returncode == 0


def ensure_worktree(base_path: Path, tree_path: Path, branch: str) -> None:
    """Ensure the worktree exists for the given branch."""
    if tree_path.exists():
        click.echo(f"Worktree already exists at {tree_path}", err=True)
        return

    click.echo(f"Creating worktree for branch '{branch}' at {tree_path}...", err=True)
    tree_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if branch exists locally
    if branch_exists_locally(base_path, branch):
        # Branch exists locally, just add worktree
        run_git("worktree", "add", str(tree_path), branch, cwd=base_path)
        return

    # Check if branch exists remotely
    result = run_git("ls-remote", "--heads", "origin", branch, cwd=base_path, capture=True)

    if result.stdout.strip():
        # Branch exists on remote, create worktree tracking it
        run_git("worktree", "add", "--track", "-b", branch, str(tree_path), f"origin/{branch}", cwd=base_path)
    else:
        # Branch doesn't exist, create new branch from default
        default_branch = get_default_branch(base_path)
        run_git("worktree", "add", "-b", branch, str(tree_path), default_branch, cwd=base_path)


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Git workspace manager using worktrees."""
    if ctx.invoked_subcommand is None:
        # Default to shell command if no subcommand given
        ctx.invoke(shell)


@main.command()
@click.argument("repo")
@click.argument("branch", required=False)
def shell(repo: str, branch: str | None = None) -> None:
    """Open a shell in a worktree for the given repo and branch.

    REPO: Git repository URL (e.g., git@github.com:user/repo.git)
    BRANCH: Branch name (defaults to repo's default branch)
    """
    root = get_gitwsp_root()
    repo_name = extract_repo_name(repo)

    base_path = root / "bases" / repo_name
    ensure_base_repo(repo, base_path)

    # Determine branch
    if branch is None:
        branch = get_default_branch(base_path)

    tree_path = root / "trees" / repo_name / branch
    ensure_worktree(base_path, tree_path, branch)

    # Print summary
    click.echo("")
    click.echo(f"Base:   {base_path}")
    click.echo(f"Tree:   {tree_path}")
    click.echo(f"Branch: {branch}")
    click.echo("")

    # Change to worktree directory and exec shell
    os.chdir(tree_path)
    user_shell = os.environ.get("SHELL", "/bin/sh")
    os.execvp(user_shell, [user_shell])


if __name__ == "__main__":
    main()

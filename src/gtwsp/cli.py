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


def extract_repo_id(repo: str) -> str:
    """Extract a unique repository identifier from a git URL.

    Returns a flat string like 'github_com_user_repo' that uniquely identifies
    the repository across different hosts and users.
    """
    # Handle SSH URLs like git@github.com:user/repo.git
    if repo.startswith("git@"):
        # git@github.com:user/repo.git -> github.com_user_repo
        host_and_path = repo[4:]  # Remove 'git@'
        host, path = host_and_path.split(":", 1)
        path = path.rstrip("/").removesuffix(".git")
        raw_id = f"{host}/{path}"
    elif (parsed := urlparse(repo)).netloc:
        # Handle HTTPS/HTTP URLs
        path = parsed.path.rstrip("/").removesuffix(".git").lstrip("/")
        raw_id = f"{parsed.netloc}/{path}"
    else:
        # Fallback: treat as a path
        raw_id = repo.rstrip("/").removesuffix(".git").lstrip("/")

    # Sanitize: replace . / : with underscores
    return raw_id.replace(".", "_").replace("/", "_").replace(":", "_")


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
        run_git("clone", "--filter=blob:none", repo_url, str(base_path))
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
    repo_id = extract_repo_id(repo)
    repo_path = root / "repos" / repo_id

    trunk_path = repo_path / "trunk"
    ensure_base_repo(repo, trunk_path)

    # Determine branch
    if branch is None:
        branch = get_default_branch(trunk_path)

    tree_path = repo_path / "tree_branches" / branch
    ensure_worktree(trunk_path, tree_path, branch)

    # Print summary
    click.echo("")
    click.echo(f"Trunk:  {trunk_path}")
    click.echo(f"Tree:   {tree_path}")
    click.echo(f"Branch: {branch}")
    click.echo("")

    # Change to worktree directory and exec shell
    os.chdir(tree_path)
    user_shell = os.environ.get("SHELL", "/bin/sh")
    os.execvp(user_shell, [user_shell])


if __name__ == "__main__":
    main()

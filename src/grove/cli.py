import os
import subprocess
from pathlib import Path

import click

from grove.config import extract_repo_id, get_grove_root
from grove.git import ensure_base_repo, ensure_worktree, get_default_branch
from grove.status import (
    BranchStatus,
    get_all_repos,
    get_repo_branches,
    get_repo_branches_fast,
)


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Manage git worktrees with ease.

    \b
    Examples:
        grove shell git@github.com:user/repo.git
        grove shell git@github.com:user/repo.git feature-branch
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.argument("repo")
@click.argument("branch", required=False)
def shell(repo: str, branch: str | None = None) -> None:
    """Open a shell in a git worktree."""
    root = get_grove_root()
    repo_id = extract_repo_id(repo)
    repo_path = root / "repos" / repo_id

    trunk_path = repo_path / "trunk"
    ensure_base_repo(repo, trunk_path)

    if branch is None:
        branch = get_default_branch(trunk_path)

    tree_path = repo_path / "tree_branches" / branch
    ensure_worktree(trunk_path, tree_path, branch)

    click.echo("")
    click.echo(f"Trunk:  {trunk_path}")
    click.echo(f"Tree:   {tree_path}")
    click.echo(f"Branch: {branch}")
    click.echo("")

    os.chdir(tree_path)
    user_shell = os.environ.get("SHELL", "/bin/sh")
    os.execvp(user_shell, [user_shell])


@main.command("list")
@click.option("--no-interactive", "-n", is_flag=True, help="Disable interactive mode")
def list_cmd(no_interactive: bool) -> None:
    """List all worktrees. Interactive by default - select to shell in."""
    from grove.menu import interactive_select, shell_into

    repos = get_all_repos()

    if not repos:
        click.echo("No repositories found.")
        click.echo(f"Workspace root: {get_grove_root()}")
        return

    if not no_interactive:
        selected = interactive_select()
        if selected:
            shell_into(selected)
        return

    _print_tree(repos)


def _print_tree(repos: list[tuple[str, Path]]) -> None:
    """Print tree view of repos and branches (fast, no git operations)."""
    for repo_name, repo_path in repos:
        branches = get_repo_branches_fast(repo_path)
        if not branches:
            continue
        click.echo(f"\n{repo_name}")
        for i, branch in enumerate(branches):
            is_last = i == len(branches) - 1
            prefix = "  └── " if is_last else "  ├── "
            click.echo(f"{prefix}{branch.name}")


@main.command()
@click.option("--dry-run", "-n", is_flag=True, help="Show what would be cleaned")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
def clean(dry_run: bool, force: bool) -> None:
    """Remove worktrees that are safe to clean."""
    to_clean = _get_cleanable_branches()

    if not to_clean:
        click.echo("Nothing to clean.")
        return

    click.echo("Worktrees to clean:")
    for branch in to_clean:
        click.echo(f"  - {branch.path}")

    if dry_run:
        click.echo(f"\nWould remove {len(to_clean)} worktree(s).")
        return

    if not force:
        click.confirm(f"\nRemove {len(to_clean)} worktree(s)?", abort=True)

    for branch in to_clean:
        trunk = branch.path.parent.parent / "trunk"
        click.echo(f"Removing {branch.name}...", nl=False)
        subprocess.run(
            ["git", "worktree", "remove", str(branch.path)],
            cwd=trunk,
            capture_output=True,
        )
        subprocess.run(
            ["git", "branch", "-d", branch.name], cwd=trunk, capture_output=True
        )
        click.echo(" done")

    click.echo(f"\nCleaned {len(to_clean)} worktree(s).")


def _get_cleanable_branches() -> list[BranchStatus]:
    """Get all branches that are safe to clean."""
    to_clean: list[BranchStatus] = []
    for _, repo_path in get_all_repos():
        for branch in get_repo_branches(repo_path):
            if branch.is_safe_to_clean:
                to_clean.append(branch)
    return to_clean


if __name__ == "__main__":
    main()

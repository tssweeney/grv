import os
from pathlib import Path

from simple_term_menu import TerminalMenu  # type: ignore[import-untyped]

from grove.status import BranchInfo, get_all_repos, get_repo_branches_fast


def build_menu_entries() -> list[tuple[str, BranchInfo]]:
    """Build list of menu entries with display text and branch info (fast)."""
    entries: list[tuple[str, BranchInfo]] = []

    for repo_name, repo_path in get_all_repos():
        branches = get_repo_branches_fast(repo_path)
        for branch in branches:
            display = f"{repo_name}/{branch.name}"
            entries.append((display, branch))

    return entries


def interactive_select() -> Path | None:
    """Show interactive menu and return selected branch path, or None if cancelled."""
    entries = build_menu_entries()

    if not entries:
        return None

    display_items = [e[0] for e in entries]
    menu = TerminalMenu(
        display_items,
        title="Select a worktree (↑/↓ to navigate, Enter to select, q to quit):",
    )
    selected_index: int | None = menu.show()

    if selected_index is None:
        return None

    return entries[selected_index][1].path


def shell_into(path: Path) -> None:
    """Change to directory and exec shell."""
    os.chdir(path)
    user_shell = os.environ.get("SHELL", "/bin/sh")
    os.execvp(user_shell, [user_shell])

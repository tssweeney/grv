import os
from pathlib import Path

from simple_term_menu import TerminalMenu  # type: ignore[import-untyped]

from grove.config import get_grove_root
from grove.status import BranchInfo, get_all_repos, get_repo_branches_fast


def build_menu_entries() -> list[tuple[str, BranchInfo | None]]:
    """Build tree-formatted menu entries. None = repo header (not selectable)."""
    entries: list[tuple[str, BranchInfo | None]] = []
    repos = [(n, p) for n, p in get_all_repos() if get_repo_branches_fast(p)]

    for ri, (repo_name, repo_path) in enumerate(repos):
        branches = get_repo_branches_fast(repo_path)
        is_last_repo = ri == len(repos) - 1
        repo_prefix = "└── " if is_last_repo else "├── "
        entries.append((f"{repo_prefix}{repo_name}", None))
        branch_indent = "    " if is_last_repo else "│   "
        for bi, branch in enumerate(branches):
            is_last = bi == len(branches) - 1
            prefix = f"{branch_indent}{'└─' if is_last else '├─'} "
            entries.append((f"{prefix}{branch.name}", branch))
    return entries


def interactive_select() -> Path | None:
    """Show interactive tree menu and return selected branch path."""
    entries = build_menu_entries()
    if not entries:
        return None

    display = [e[0] for e in entries]
    # Find first selectable (branch) index
    first_branch = next((i for i, e in enumerate(entries) if e[1] is not None), 0)
    title = f"Grove Workspace\n{get_grove_root()}\n"
    menu = TerminalMenu(
        display,
        title=title,
        cursor_index=first_branch,
        menu_cursor_style=("fg_cyan", "bold"),
    )
    selected: int | None = menu.show()
    if selected is None:
        return None
    branch = entries[selected][1]
    return branch.path if branch else None


def shell_into(path: Path) -> None:
    """Change to directory and exec shell."""
    os.chdir(path)
    user_shell = os.environ.get("SHELL", "/bin/sh")
    os.execvp(user_shell, [user_shell])

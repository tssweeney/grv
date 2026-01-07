# grove

Git workspace manager using worktrees. Clone once, work on many branches simultaneously.

## Install

```bash
uv tool install grove
```

## Usage

```bash
# Open a shell in a worktree (clones repo if needed)
grove shell git@github.com:user/repo.git
grove shell git@github.com:user/repo.git feature-branch

# List all worktrees with status
grove list

# Clean up merged worktrees
grove clean
grove clean --dry-run
```

## How it works

`grove` manages git worktrees in `~/.grove/`:

```
~/.grove/repos/github_com_user_repo/
├── trunk/              # Base clone (blobless for speed)
└── tree_branches/
    ├── main/           # Worktree for main
    └── feature-branch/ # Worktree for feature-branch
```

Each branch gets its own directory. Switch between branches by switching directories.

## Commands

| Command | Description |
|---------|-------------|
| `shell REPO [BRANCH]` | Open shell in worktree |
| `list` | Show all worktrees with status |
| `clean` | Remove safe-to-clean worktrees |

## Configuration

Set `GROVE_ROOT` to change the workspace location (default: `~/.grove`).

## License

MIT

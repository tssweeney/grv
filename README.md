# gtwsp

Git workspace manager using worktrees. Clone once, work on many branches simultaneously.

## Install

```bash
uv tool install gtwsp
```

## Usage

```bash
# Open a shell in a worktree (clones repo if needed)
gtwsp shell git@github.com:user/repo.git
gtwsp shell git@github.com:user/repo.git feature-branch

# List all worktrees with status
gtwsp list

# Clean up merged worktrees
gtwsp clean
gtwsp clean --dry-run
```

## How it works

`gtwsp` manages git worktrees in `~/.gitwsp/`:

```
~/.gitwsp/repos/github_com_user_repo/
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

Set `GITWSP_ROOT` to change the workspace location (default: `~/.gitwsp`).

## License

MIT

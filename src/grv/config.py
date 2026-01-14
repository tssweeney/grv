import os
from pathlib import Path
from urllib.parse import urlparse

from grv.constants import (
    DEFAULT_GRV_ROOT,
    GH_SHORTHAND_PREFIX,
    GIT_SSH_PREFIX,
    GIT_SUFFIX,
    GITHUB_SSH_HOST,
)


def get_grv_root() -> Path:
    """Get the GRV_ROOT directory, defaulting to ~/.grv."""
    root = os.environ.get("GRV_ROOT", os.path.expanduser(DEFAULT_GRV_ROOT))
    return Path(root)


def extract_repo_id(repo: str) -> str:
    """Extract a unique repository identifier from a git URL.

    Returns a flat string like 'github_com_user_repo' that uniquely identifies
    the repository across different hosts and users.
    """
    if repo.startswith(GIT_SSH_PREFIX):
        host_and_path = repo[len(GIT_SSH_PREFIX) :]
        host, path = host_and_path.split(":", 1)
        path = path.rstrip("/").removesuffix(GIT_SUFFIX)
        raw_id = f"{host}/{path}"
    elif (parsed := urlparse(repo)).netloc:
        path = parsed.path.rstrip("/").removesuffix(GIT_SUFFIX).lstrip("/")
        raw_id = f"{parsed.netloc}/{path}"
    else:
        raw_id = repo.rstrip("/").removesuffix(GIT_SUFFIX).lstrip("/")

    return raw_id.replace(".", "_").replace("/", "_").replace(":", "_")


def expand_gh_shorthand(repo: str) -> tuple[str, str | None]:
    """Expand GitHub shorthand to full URL and extract optional from_branch.

    Args:
        repo: Repository string, possibly in gh:OWNER/REPO[@branch] format

    Returns:
        Tuple of (expanded_url, from_branch). from_branch is None if not specified.
        If input is not a shorthand, returns (repo, None).

    Examples:
        "gh:user/repo" -> ("git@github.com:user/repo.git", None)
        "gh:user/repo@main" -> ("git@github.com:user/repo.git", "main")
        "https://github.com/user/repo" -> ("https://github.com/user/repo", None)
    """
    if not repo.startswith(GH_SHORTHAND_PREFIX):
        return (repo, None)

    # Remove the "gh:" prefix
    remainder = repo[len(GH_SHORTHAND_PREFIX) :]

    # Split on @ to get owner/repo and optional branch
    if "@" in remainder:
        owner_repo, from_branch = remainder.split("@", 1)
        # Handle empty from_branch (e.g., "gh:user/repo@")
        from_branch = from_branch if from_branch else None
    else:
        owner_repo = remainder
        from_branch = None

    # Build the full SSH URL
    expanded_url = f"{GIT_SSH_PREFIX}{GITHUB_SSH_HOST}:{owner_repo}{GIT_SUFFIX}"
    return (expanded_url, from_branch)

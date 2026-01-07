import os
from pathlib import Path
from urllib.parse import urlparse


def get_grove_root() -> Path:
    """Get the GROVE_ROOT directory, defaulting to ~/.grove."""
    root = os.environ.get("GROVE_ROOT", os.path.expanduser("~/.grove"))
    return Path(root)


def extract_repo_id(repo: str) -> str:
    """Extract a unique repository identifier from a git URL.

    Returns a flat string like 'github_com_user_repo' that uniquely identifies
    the repository across different hosts and users.
    """
    if repo.startswith("git@"):
        host_and_path = repo[4:]
        host, path = host_and_path.split(":", 1)
        path = path.rstrip("/").removesuffix(".git")
        raw_id = f"{host}/{path}"
    elif (parsed := urlparse(repo)).netloc:
        path = parsed.path.rstrip("/").removesuffix(".git").lstrip("/")
        raw_id = f"{parsed.netloc}/{path}"
    else:
        raw_id = repo.rstrip("/").removesuffix(".git").lstrip("/")

    return raw_id.replace(".", "_").replace("/", "_").replace(":", "_")

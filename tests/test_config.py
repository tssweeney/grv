from pathlib import Path

import pytest

from grove.config import extract_repo_id, get_grove_root


class TestGetGroveRoot:
    def test_default_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GROVE_ROOT", raising=False)
        result = get_grove_root()
        assert result == Path.home() / ".grove"

    def test_custom_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GROVE_ROOT", "/custom/path")
        result = get_grove_root()
        assert result == Path("/custom/path")


class TestExtractRepoId:
    def test_ssh_url(self) -> None:
        result = extract_repo_id("git@github.com:user/repo.git")
        assert result == "github_com_user_repo"

    def test_https_url(self) -> None:
        result = extract_repo_id("https://github.com/user/repo.git")
        assert result == "github_com_user_repo"

    def test_https_without_git_suffix(self) -> None:
        result = extract_repo_id("https://github.com/user/repo")
        assert result == "github_com_user_repo"

    def test_gitlab_url(self) -> None:
        result = extract_repo_id("git@gitlab.com:org/project.git")
        assert result == "gitlab_com_org_project"

    def test_nested_path(self) -> None:
        result = extract_repo_id("https://gitlab.com/org/sub/repo.git")
        assert result == "gitlab_com_org_sub_repo"

    def test_fallback_path(self) -> None:
        result = extract_repo_id("some/local/repo.git")
        assert result == "some_local_repo"

    def test_trailing_slash(self) -> None:
        result = extract_repo_id("https://github.com/user/repo/")
        assert result == "github_com_user_repo"

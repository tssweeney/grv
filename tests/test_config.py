from pathlib import Path

import pytest

from grv.config import expand_gh_shorthand, extract_repo_id, get_grv_root


class TestGetGrvRoot:
    def test_default_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GRV_ROOT", raising=False)
        result = get_grv_root()
        assert result == Path.home() / ".grv"

    def test_custom_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GRV_ROOT", "/custom/path")
        result = get_grv_root()
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


class TestExpandGhShorthand:
    def test_basic_shorthand(self) -> None:
        url, from_branch = expand_gh_shorthand("gh:user/repo")
        assert url == "git@github.com:user/repo.git"
        assert from_branch is None

    def test_shorthand_with_from_branch(self) -> None:
        url, from_branch = expand_gh_shorthand("gh:user/repo@main")
        assert url == "git@github.com:user/repo.git"
        assert from_branch == "main"

    def test_shorthand_with_complex_branch(self) -> None:
        url, from_branch = expand_gh_shorthand("gh:user/repo@feature/foo")
        assert url == "git@github.com:user/repo.git"
        assert from_branch == "feature/foo"

    def test_org_repo(self) -> None:
        url, from_branch = expand_gh_shorthand("gh:my-org/my-repo")
        assert url == "git@github.com:my-org/my-repo.git"
        assert from_branch is None

    def test_not_shorthand_ssh(self) -> None:
        url, from_branch = expand_gh_shorthand("git@github.com:user/repo.git")
        assert url == "git@github.com:user/repo.git"
        assert from_branch is None

    def test_not_shorthand_https(self) -> None:
        url, from_branch = expand_gh_shorthand("https://github.com/user/repo")
        assert url == "https://github.com/user/repo"
        assert from_branch is None

    def test_empty_from_branch(self) -> None:
        url, from_branch = expand_gh_shorthand("gh:user/repo@")
        assert url == "git@github.com:user/repo.git"
        assert from_branch is None

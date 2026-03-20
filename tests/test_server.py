"""Tests for MCP server tool functions."""

import json
from unittest.mock import patch

import pytest

from mooring.server import (
    health,
    repo_blame,
    repo_branches,
    repo_diff,
    repo_log,
    repo_stash,
    repo_status,
    gh_pr_list,
    gh_pr_detail,
    gh_pr_create,
    gh_issues,
    gh_actions,
)


class TestHealth:
    def test_returns_version_and_status(self):
        result = json.loads(health())
        assert result["server"] == "Mooring"
        assert result["status"] == "ok"
        assert "version" in result


class TestServerRepoStatus:
    def test_clean_repo(self, test_repo):
        result = json.loads(repo_status(test_repo.working_dir))
        assert result["branch"] == "main"
        assert "error" not in result

    def test_invalid_path_returns_error(self):
        result = json.loads(repo_status("/nonexistent"))
        assert "error" in result


class TestServerRepoLog:
    def test_returns_json(self, test_repo):
        result = json.loads(repo_log(test_repo.working_dir))
        assert isinstance(result, list)
        assert len(result) >= 1


class TestServerRepoDiff:
    def test_returns_string(self, test_repo):
        result = repo_diff(test_repo.working_dir, from_ref="main", to_ref="feature/add-tests")
        assert "test_main.py" in result

    def test_error_returns_json(self):
        result = repo_diff("/nonexistent")
        parsed = json.loads(result)
        assert "error" in parsed


class TestServerRepoBlame:
    def test_returns_json(self, test_repo):
        result = json.loads(repo_blame(test_repo.working_dir, "README.md"))
        assert isinstance(result, list)
        assert len(result) > 0

    def test_error_returns_json(self, test_repo):
        result = json.loads(repo_blame(test_repo.working_dir, "../../etc/passwd"))
        assert "error" in result


class TestServerRepoBranches:
    def test_returns_json(self, test_repo):
        result = json.loads(repo_branches(test_repo.working_dir))
        assert isinstance(result, list)
        names = [b["name"] for b in result]
        assert "main" in names


class TestServerRepoStash:
    def test_returns_json(self, test_repo):
        result = json.loads(repo_stash(test_repo.working_dir))
        assert result["count"] == 0

    def test_error_returns_json(self, test_repo):
        result = json.loads(repo_stash(test_repo.working_dir, action="bad"))
        assert "error" in result


class TestServerGitHubTools:
    @patch("mooring.server._gh_pr_list")
    def test_gh_pr_list(self, mock_fn):
        mock_fn.return_value = [{"number": 1, "title": "Test PR"}]
        result = json.loads(gh_pr_list("owner/repo"))
        assert result[0]["number"] == 1

    @patch("mooring.server._gh_pr_list")
    def test_gh_pr_list_error(self, mock_fn):
        from mooring.github_ops import GitHubOpsError
        mock_fn.side_effect = GitHubOpsError("token missing")
        result = json.loads(gh_pr_list("owner/repo"))
        assert "error" in result

    @patch("mooring.server._gh_pr_detail")
    def test_gh_pr_detail(self, mock_fn):
        mock_fn.return_value = {"number": 1, "title": "Test PR", "body": "desc"}
        result = json.loads(gh_pr_detail("owner/repo", 1))
        assert result["number"] == 1

    @patch("mooring.server._gh_pr_detail")
    def test_gh_pr_detail_error(self, mock_fn):
        from mooring.github_ops import GitHubOpsError
        mock_fn.side_effect = GitHubOpsError("not found")
        result = json.loads(gh_pr_detail("owner/repo", 999))
        assert "error" in result

    @patch("mooring.server._gh_pr_create")
    def test_gh_pr_create(self, mock_fn):
        mock_fn.return_value = {"number": 5, "url": "https://github.com/o/r/pull/5"}
        result = json.loads(gh_pr_create("owner/repo", "title", "body", "feature"))
        assert result["number"] == 5

    @patch("mooring.server._gh_pr_create")
    def test_gh_pr_create_error(self, mock_fn):
        from mooring.github_ops import GitHubOpsError
        mock_fn.side_effect = GitHubOpsError("permission denied")
        result = json.loads(gh_pr_create("owner/repo", "t", "b", "h"))
        assert "error" in result

    @patch("mooring.server._gh_issues")
    def test_gh_issues(self, mock_fn):
        mock_fn.return_value = [{"number": 10, "title": "Bug"}]
        result = json.loads(gh_issues("owner/repo"))
        assert result[0]["number"] == 10

    @patch("mooring.server._gh_issues")
    def test_gh_issues_error(self, mock_fn):
        from mooring.github_ops import GitHubOpsError
        mock_fn.side_effect = GitHubOpsError("bad request")
        result = json.loads(gh_issues("owner/repo"))
        assert "error" in result

    @patch("mooring.server._gh_actions")
    def test_gh_actions(self, mock_fn):
        mock_fn.return_value = [{"id": 1, "status": "completed"}]
        result = json.loads(gh_actions("owner/repo"))
        assert result[0]["id"] == 1

    @patch("mooring.server._gh_actions")
    def test_gh_actions_error(self, mock_fn):
        from mooring.github_ops import GitHubOpsError
        mock_fn.side_effect = GitHubOpsError("rate limited")
        result = json.loads(gh_actions("owner/repo"))
        assert "error" in result

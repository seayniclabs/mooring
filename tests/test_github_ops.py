"""Tests for GitHub API operations with mocked PyGithub."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from mooring.github_ops import (
    GitHubOpsError,
    _handle_rate_limit,
    _safe_error,
    _validate_repo_format,
    gh_actions,
    gh_issues,
    gh_pr_create,
    gh_pr_detail,
    gh_pr_list,
)


def _make_label(name):
    label = MagicMock()
    label.name = name
    return label


def _make_user(login):
    user = MagicMock()
    user.login = login
    return user


def _make_pr(number, title, author, state="open", draft=False, labels=None):
    pr = MagicMock()
    pr.number = number
    pr.title = title
    pr.state = state
    pr.draft = draft
    pr.html_url = f"https://github.com/owner/repo/pull/{number}"
    pr.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    pr.updated_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
    pr.user = _make_user(author)
    pr.labels = [_make_label(l) for l in (labels or [])]
    return pr


def _make_issue(number, title, author, state="open", labels=None, is_pr=False):
    issue = MagicMock()
    issue.number = number
    issue.title = title
    issue.state = state
    issue.html_url = f"https://github.com/owner/repo/issues/{number}"
    issue.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    issue.updated_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
    issue.user = _make_user(author)
    issue.labels = [_make_label(l) for l in (labels or [])]
    issue.pull_request = MagicMock() if is_pr else None
    return issue


class TestGhPrList:
    @patch("mooring.github_ops._get_client")
    def test_returns_prs(self, mock_client, mock_github_token):
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [
            _make_pr(42, "Add feature", "dev1", labels=["enhancement"]),
        ]
        mock_client.return_value.get_repo.return_value = mock_repo

        result = gh_pr_list("owner/repo")
        assert len(result) == 1
        assert result[0]["number"] == 42
        assert result[0]["title"] == "Add feature"
        assert result[0]["author"] == "dev1"
        assert result[0]["labels"] == ["enhancement"]

    @patch("mooring.github_ops._get_client")
    def test_empty_pr_list(self, mock_client, mock_github_token):
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = []
        mock_client.return_value.get_repo.return_value = mock_repo

        result = gh_pr_list("owner/repo")
        assert result == []

    @patch("mooring.github_ops._get_client")
    def test_filter_by_author(self, mock_client, mock_github_token):
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [
            _make_pr(1, "PR by dev1", "dev1"),
            _make_pr(2, "PR by dev2", "dev2"),
        ]
        mock_client.return_value.get_repo.return_value = mock_repo

        result = gh_pr_list("owner/repo", author="dev1")
        assert len(result) == 1
        assert result[0]["author"] == "dev1"


class TestGhIssues:
    @patch("mooring.github_ops._get_client")
    def test_returns_issues(self, mock_client, mock_github_token):
        mock_repo = MagicMock()
        mock_repo.get_issues.return_value = [
            _make_issue(10, "Bug report", "reporter", labels=["bug"]),
        ]
        mock_client.return_value.get_repo.return_value = mock_repo

        result = gh_issues("owner/repo")
        assert len(result) == 1
        assert result[0]["number"] == 10
        assert result[0]["title"] == "Bug report"
        assert result[0]["author"] == "reporter"
        assert result[0]["labels"] == ["bug"]

    @patch("mooring.github_ops._get_client")
    def test_empty_issues(self, mock_client, mock_github_token):
        mock_repo = MagicMock()
        mock_repo.get_issues.return_value = []
        mock_client.return_value.get_repo.return_value = mock_repo

        result = gh_issues("owner/repo")
        assert result == []

    @patch("mooring.github_ops._get_client")
    def test_filters_out_pull_requests(self, mock_client, mock_github_token):
        mock_repo = MagicMock()
        mock_repo.get_issues.return_value = [
            _make_issue(10, "Real issue", "reporter"),
            _make_issue(11, "Actually a PR", "dev1", is_pr=True),
        ]
        mock_client.return_value.get_repo.return_value = mock_repo

        result = gh_issues("owner/repo")
        assert len(result) == 1
        assert result[0]["number"] == 10


class TestGhPrDetail:
    @patch("mooring.github_ops._get_client")
    def test_returns_detail(self, mock_client, mock_github_token):
        mock_pr = MagicMock()
        mock_pr.number = 42
        mock_pr.title = "Feature PR"
        mock_pr.body = "Description"
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.mergeable = True
        mock_pr.additions = 10
        mock_pr.deletions = 2
        mock_pr.changed_files = 3
        mock_pr.commits = 0
        mock_pr.html_url = "https://github.com/owner/repo/pull/42"
        mock_pr.user = _make_user("dev1")
        mock_pr.labels = [_make_label("enhancement")]
        mock_pr.get_reviews.return_value = []
        mock_pr.get_issue_comments.return_value = []

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.return_value.get_repo.return_value = mock_repo

        result = gh_pr_detail("owner/repo", 42)
        assert result["number"] == 42
        assert result["title"] == "Feature PR"
        assert result["additions"] == 10


class TestGhPrCreate:
    @patch("mooring.github_ops._get_client")
    def test_creates_pr(self, mock_client, mock_github_token):
        mock_pr = MagicMock()
        mock_pr.number = 5
        mock_pr.title = "New PR"
        mock_pr.html_url = "https://github.com/owner/repo/pull/5"
        mock_pr.state = "open"

        mock_repo = MagicMock()
        mock_repo.create_pull.return_value = mock_pr
        mock_client.return_value.get_repo.return_value = mock_repo

        result = gh_pr_create("owner/repo", "New PR", "body", "feature")
        assert result["number"] == 5
        assert result["state"] == "open"

    @patch("mooring.github_ops._get_client")
    def test_creates_pr_with_labels_and_reviewers(self, mock_client, mock_github_token):
        mock_pr = MagicMock()
        mock_pr.number = 6
        mock_pr.title = "PR"
        mock_pr.html_url = "https://github.com/owner/repo/pull/6"
        mock_pr.state = "open"

        mock_repo = MagicMock()
        mock_repo.create_pull.return_value = mock_pr
        mock_client.return_value.get_repo.return_value = mock_repo

        result = gh_pr_create("owner/repo", "PR", "body", "feat", labels=["bug"], reviewers=["dev1"])
        mock_pr.set_labels.assert_called_once_with("bug")
        mock_pr.create_review_request.assert_called_once_with(reviewers=["dev1"])


class TestGhIssuesCreate:
    @patch("mooring.github_ops._get_client")
    def test_creates_issue(self, mock_client, mock_github_token):
        mock_issue = MagicMock()
        mock_issue.number = 20
        mock_issue.title = "New Bug"
        mock_issue.html_url = "https://github.com/owner/repo/issues/20"
        mock_issue.state = "open"

        mock_repo = MagicMock()
        mock_repo.create_issue.return_value = mock_issue
        mock_client.return_value.get_repo.return_value = mock_repo

        result = gh_issues("owner/repo", action="create", title="New Bug", body="Details")
        assert result["number"] == 20

    @patch("mooring.github_ops._get_client")
    def test_create_without_title_raises(self, mock_client, mock_github_token):
        mock_repo = MagicMock()
        mock_client.return_value.get_repo.return_value = mock_repo

        with pytest.raises(GitHubOpsError, match="Title is required"):
            gh_issues("owner/repo", action="create")

    @patch("mooring.github_ops._get_client")
    def test_update_issue(self, mock_client, mock_github_token):
        mock_issue = MagicMock()
        mock_issue.number = 10
        mock_issue.title = "Updated Bug"
        mock_issue.html_url = "https://github.com/owner/repo/issues/10"
        mock_issue.state = "open"

        mock_repo = MagicMock()
        mock_repo.get_issue.return_value = mock_issue
        mock_client.return_value.get_repo.return_value = mock_repo

        result = gh_issues("owner/repo", action="update", number=10, title="Updated Bug")
        assert result["number"] == 10
        mock_issue.edit.assert_called_once()

    @patch("mooring.github_ops._get_client")
    def test_update_without_number_raises(self, mock_client, mock_github_token):
        mock_repo = MagicMock()
        mock_client.return_value.get_repo.return_value = mock_repo

        with pytest.raises(GitHubOpsError, match="Issue number is required"):
            gh_issues("owner/repo", action="update")

    @patch("mooring.github_ops._get_client")
    def test_invalid_action_raises(self, mock_client, mock_github_token):
        mock_repo = MagicMock()
        mock_client.return_value.get_repo.return_value = mock_repo

        with pytest.raises(GitHubOpsError, match="Unknown action"):
            gh_issues("owner/repo", action="delete")


class TestGhActions:
    @patch("mooring.github_ops._get_client")
    def test_returns_runs(self, mock_client, mock_github_token):
        mock_run = MagicMock()
        mock_run.id = 100
        mock_run.name = "Test"
        mock_run.status = "completed"
        mock_run.conclusion = "success"
        mock_run.head_branch = "main"
        mock_run.event = "push"
        mock_run.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        mock_run.updated_at = datetime(2025, 1, 1, 0, 5, tzinfo=timezone.utc)
        mock_run.html_url = "https://github.com/owner/repo/actions/runs/100"

        mock_repo = MagicMock()
        mock_repo.get_workflow_runs.return_value = [mock_run]
        mock_client.return_value.get_repo.return_value = mock_repo

        result = gh_actions("owner/repo")
        assert len(result) == 1
        assert result[0]["id"] == 100
        assert result[0]["duration_seconds"] == 300.0

    @patch("mooring.github_ops._get_client")
    def test_with_workflow_filter(self, mock_client, mock_github_token):
        mock_run = MagicMock()
        mock_run.id = 200
        mock_run.name = "Build"
        mock_run.status = "completed"
        mock_run.conclusion = "success"
        mock_run.head_branch = "main"
        mock_run.event = "push"
        mock_run.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        mock_run.updated_at = datetime(2025, 1, 1, 0, 10, tzinfo=timezone.utc)
        mock_run.html_url = "https://github.com/owner/repo/actions/runs/200"

        mock_workflow = MagicMock()
        mock_workflow.get_runs.return_value = [mock_run]
        mock_repo = MagicMock()
        mock_repo.get_workflow.return_value = mock_workflow
        mock_client.return_value.get_repo.return_value = mock_repo

        result = gh_actions("owner/repo", workflow="build.yml")
        assert len(result) == 1
        assert result[0]["id"] == 200


class TestGhExceptionHandling:
    @patch("mooring.github_ops._get_client")
    def test_pr_list_rate_limit(self, mock_client, mock_github_token):
        from github import RateLimitExceededException
        mock_client.return_value.get_repo.side_effect = RateLimitExceededException(
            403, {"message": "rate limit"}, None
        )
        with pytest.raises(GitHubOpsError, match="rate limit"):
            gh_pr_list("owner/repo")

    @patch("mooring.github_ops._get_client")
    def test_pr_list_github_error(self, mock_client, mock_github_token):
        from github import GithubException
        mock_client.return_value.get_repo.side_effect = GithubException(
            404, {"message": "Not Found"}, None
        )
        with pytest.raises(GitHubOpsError):
            gh_pr_list("owner/repo")

    @patch("mooring.github_ops._get_client")
    def test_pr_detail_rate_limit(self, mock_client, mock_github_token):
        from github import RateLimitExceededException
        mock_client.return_value.get_repo.side_effect = RateLimitExceededException(
            403, {"message": "rate limit"}, None
        )
        with pytest.raises(GitHubOpsError, match="rate limit"):
            gh_pr_detail("owner/repo", 1)

    @patch("mooring.github_ops._get_client")
    def test_pr_detail_github_error(self, mock_client, mock_github_token):
        from github import GithubException
        mock_client.return_value.get_repo.side_effect = GithubException(
            404, {"message": "Not Found"}, None
        )
        with pytest.raises(GitHubOpsError):
            gh_pr_detail("owner/repo", 1)

    @patch("mooring.github_ops._get_client")
    def test_pr_create_rate_limit(self, mock_client, mock_github_token):
        from github import RateLimitExceededException
        mock_client.return_value.get_repo.side_effect = RateLimitExceededException(
            403, {"message": "rate limit"}, None
        )
        with pytest.raises(GitHubOpsError, match="rate limit"):
            gh_pr_create("owner/repo", "t", "b", "h")

    @patch("mooring.github_ops._get_client")
    def test_pr_create_github_error(self, mock_client, mock_github_token):
        from github import GithubException
        mock_client.return_value.get_repo.side_effect = GithubException(
            422, {"message": "Validation Failed"}, None
        )
        with pytest.raises(GitHubOpsError):
            gh_pr_create("owner/repo", "t", "b", "h")

    @patch("mooring.github_ops._get_client")
    def test_issues_rate_limit(self, mock_client, mock_github_token):
        from github import RateLimitExceededException
        mock_client.return_value.get_repo.side_effect = RateLimitExceededException(
            403, {"message": "rate limit"}, None
        )
        with pytest.raises(GitHubOpsError, match="rate limit"):
            gh_issues("owner/repo")

    @patch("mooring.github_ops._get_client")
    def test_issues_github_error(self, mock_client, mock_github_token):
        from github import GithubException
        mock_client.return_value.get_repo.side_effect = GithubException(
            500, {"message": "Server Error"}, None
        )
        with pytest.raises(GitHubOpsError):
            gh_issues("owner/repo")

    @patch("mooring.github_ops._get_client")
    def test_actions_rate_limit(self, mock_client, mock_github_token):
        from github import RateLimitExceededException
        mock_client.return_value.get_repo.side_effect = RateLimitExceededException(
            403, {"message": "rate limit"}, None
        )
        with pytest.raises(GitHubOpsError, match="rate limit"):
            gh_actions("owner/repo")

    @patch("mooring.github_ops._get_client")
    def test_actions_github_error(self, mock_client, mock_github_token):
        from github import GithubException
        mock_client.return_value.get_repo.side_effect = GithubException(
            404, {"message": "Not Found"}, None
        )
        with pytest.raises(GitHubOpsError):
            gh_actions("owner/repo")


class TestRateLimitHandling:
    def test_403_rate_limit_message(self):
        from github import GithubException
        exc = GithubException(403, {"message": "rate limit exceeded"}, None)
        result = _handle_rate_limit(exc)
        assert "rate limit exceeded" in result.lower()

    def test_non_403_returns_safe_error(self):
        from github import GithubException
        exc = GithubException(404, {"message": "not found"}, None)
        result = _handle_rate_limit(exc)
        # Non-403 falls through to _safe_error
        assert "not found" in result.lower() or len(result) > 0


class TestMissingToken:
    def test_no_token_raises_clear_error(self, no_github_token):
        with pytest.raises(GitHubOpsError, match="GITHUB_TOKEN.*not set"):
            gh_pr_list("owner/repo")

    def test_no_token_issues(self, no_github_token):
        with pytest.raises(GitHubOpsError, match="GITHUB_TOKEN.*not set"):
            gh_issues("owner/repo")


class TestTokenNotExposed:
    def test_token_masked_in_error(self, mock_github_token):
        """Verify the safe_error function masks tokens."""
        token = "ghp_FAKE_TOKEN_FOR_TESTING_ONLY"
        exc = Exception(f"Authentication failed for token {token}")
        result = _safe_error(exc)
        assert token not in result
        assert "***" in result


class TestTokenPatternMasking:
    """Test that _safe_error masks GitHub token patterns via regex."""

    def test_masks_ghp_pattern(self):
        token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
        exc = Exception(f"Error with token {token} in message")
        result = _safe_error(exc)
        assert token not in result
        assert "***" in result

    def test_masks_gho_pattern(self):
        token = "gho_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
        exc = Exception(f"Failed auth: {token}")
        result = _safe_error(exc)
        assert token not in result
        assert "***" in result

    def test_masks_github_pat_pattern(self):
        token = "github_pat_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
        exc = Exception(f"Token leaked: {token}")
        result = _safe_error(exc)
        assert token not in result
        assert "***" in result

    def test_masks_multiple_tokens(self):
        t1 = "ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        t2 = "gho_BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
        exc = Exception(f"Tokens: {t1} and {t2}")
        result = _safe_error(exc)
        assert t1 not in result
        assert t2 not in result

    def test_no_false_positive_short_prefix(self):
        """Short strings like 'ghp_abc' should not be masked (too short for real token)."""
        exc = Exception("Error with ghp_abc in text")
        result = _safe_error(exc)
        # ghp_abc is only 7 chars after prefix — real tokens are 36+
        assert "ghp_abc" in result


class TestRepoFormatValidation:
    """Test that malformed repo strings are rejected."""

    def test_valid_format(self):
        # Should not raise
        _validate_repo_format("owner/repo")

    def test_missing_slash(self, mock_github_token):
        with pytest.raises(GitHubOpsError, match="Invalid repository format"):
            _validate_repo_format("ownerrepo")

    def test_empty_string(self, mock_github_token):
        with pytest.raises(GitHubOpsError, match="Invalid repository format"):
            _validate_repo_format("")

    def test_multiple_slashes(self, mock_github_token):
        with pytest.raises(GitHubOpsError, match="Invalid repository format"):
            _validate_repo_format("owner/repo/extra")

    def test_empty_owner(self, mock_github_token):
        with pytest.raises(GitHubOpsError, match="Invalid repository format"):
            _validate_repo_format("/repo")

    def test_empty_name(self, mock_github_token):
        with pytest.raises(GitHubOpsError, match="Invalid repository format"):
            _validate_repo_format("owner/")

    def test_gh_pr_list_rejects_bad_format(self, mock_github_token):
        with pytest.raises(GitHubOpsError, match="Invalid repository format"):
            gh_pr_list("not-a-repo")

    def test_gh_issues_rejects_bad_format(self, mock_github_token):
        with pytest.raises(GitHubOpsError, match="Invalid repository format"):
            gh_issues("badformat")

    def test_gh_actions_rejects_bad_format(self, mock_github_token):
        with pytest.raises(GitHubOpsError, match="Invalid repository format"):
            gh_actions("no-slash")


class TestPrDetailWithContent:
    """Test PR detail with populated reviews, comments, and check runs."""

    @patch("mooring.github_ops._get_client")
    def test_pr_with_reviews_comments_checks(self, mock_client, mock_github_token):
        # Build review mock
        review = MagicMock()
        review.user = _make_user("reviewer1")
        review.state = "APPROVED"
        review.submitted_at = datetime(2025, 1, 3, tzinfo=timezone.utc)

        # Build comment mock
        comment = MagicMock()
        comment.user = _make_user("commenter1")
        comment.body = "Looks good!"
        comment.created_at = datetime(2025, 1, 4, tzinfo=timezone.utc)

        # Build check run mock
        check_run = MagicMock()
        check_run.name = "CI / test"
        check_run.status = "completed"
        check_run.conclusion = "success"

        # Build commit mock for check runs
        mock_commit = MagicMock()
        mock_commit.get_check_runs.return_value = [check_run]

        # Build PR mock
        mock_pr = MagicMock()
        mock_pr.number = 99
        mock_pr.title = "Full PR"
        mock_pr.body = "Detailed description"
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.mergeable = True
        mock_pr.additions = 50
        mock_pr.deletions = 10
        mock_pr.changed_files = 5
        mock_pr.commits = 2
        mock_pr.html_url = "https://github.com/owner/repo/pull/99"
        mock_pr.user = _make_user("author1")
        mock_pr.labels = [_make_label("feature"), _make_label("ready")]
        mock_pr.get_reviews.return_value = [review]
        mock_pr.get_issue_comments.return_value = [comment]
        mock_pr.get_commits.return_value.reversed = [mock_commit]

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.return_value.get_repo.return_value = mock_repo

        result = gh_pr_detail("owner/repo", 99)

        # Verify reviews
        assert len(result["reviews"]) == 1
        assert result["reviews"][0]["user"] == "reviewer1"
        assert result["reviews"][0]["state"] == "APPROVED"

        # Verify comments
        assert len(result["comments"]) == 1
        assert result["comments"][0]["user"] == "commenter1"
        assert result["comments"][0]["body"] == "Looks good!"

        # Verify checks
        assert len(result["checks"]) == 1
        assert result["checks"][0]["name"] == "CI / test"
        assert result["checks"][0]["conclusion"] == "success"

        # Verify labels
        assert result["labels"] == ["feature", "ready"]

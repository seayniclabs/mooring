"""GitHub API operations using PyGithub.

All functions require GITHUB_TOKEN environment variable.
Token is never logged or included in output.
"""

import os

from github import Auth, Github, GithubException, RateLimitExceededException


class GitHubOpsError(Exception):
    """Raised when a GitHub operation fails."""


def _get_client() -> Github:
    """Get authenticated GitHub client."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise GitHubOpsError(
            "GITHUB_TOKEN environment variable is not set. "
            "Set it to a GitHub personal access token."
        )
    return Github(auth=Auth.Token(token))


def _safe_error(exc: Exception) -> str:
    """Return error message with any token values masked."""
    msg = str(exc)
    token = os.environ.get("GITHUB_TOKEN", "")
    if token and token in msg:
        msg = msg.replace(token, "***")
    return msg


def _handle_rate_limit(exc: GithubException) -> str:
    """Detect rate limiting and return a clear message."""
    if exc.status == 403:
        return (
            "GitHub API rate limit exceeded. "
            "Wait for the rate limit to reset or use a token with higher limits."
        )
    return _safe_error(exc)


def gh_pr_list(
    repo: str,
    state: str = "open",
    author: str | None = None,
    label: str | None = None,
) -> list[dict]:
    """List pull requests."""
    client = _get_client()
    try:
        gh_repo = client.get_repo(repo)
        prs = gh_repo.get_pulls(state=state, sort="updated", direction="desc")

        results = []
        count = 0
        for pr in prs:
            if count >= 50:
                break
            count += 1
            if author and pr.user.login != author:
                continue
            if label and label not in [l.name for l in pr.labels]:
                continue
            results.append({
                "number": pr.number,
                "title": pr.title,
                "author": pr.user.login,
                "state": pr.state,
                "created_at": pr.created_at.isoformat(),
                "updated_at": pr.updated_at.isoformat(),
                "labels": [l.name for l in pr.labels],
                "draft": pr.draft,
                "url": pr.html_url,
            })
        return results

    except RateLimitExceededException as exc:
        raise GitHubOpsError(_handle_rate_limit(exc))
    except GithubException as exc:
        raise GitHubOpsError(_safe_error(exc))


def gh_pr_detail(repo: str, number: int) -> dict:
    """Get detailed PR information."""
    client = _get_client()
    try:
        gh_repo = client.get_repo(repo)
        pr = gh_repo.get_pull(number)

        # Collect reviews
        reviews = []
        for review in pr.get_reviews():
            reviews.append({
                "user": review.user.login,
                "state": review.state,
                "submitted_at": review.submitted_at.isoformat() if review.submitted_at else None,
            })

        # Collect comments
        comments = []
        for comment in pr.get_issue_comments():
            comments.append({
                "user": comment.user.login,
                "body": comment.body,
                "created_at": comment.created_at.isoformat(),
            })

        # Check runs
        checks = []
        try:
            commit = pr.get_commits().reversed[0] if pr.commits > 0 else None
            if commit:
                for run in commit.get_check_runs():
                    checks.append({
                        "name": run.name,
                        "status": run.status,
                        "conclusion": run.conclusion,
                    })
        except (GithubException, IndexError):
            pass

        return {
            "number": pr.number,
            "title": pr.title,
            "body": pr.body or "",
            "author": pr.user.login,
            "state": pr.state,
            "merged": pr.merged,
            "mergeable": pr.mergeable,
            "additions": pr.additions,
            "deletions": pr.deletions,
            "changed_files": pr.changed_files,
            "labels": [l.name for l in pr.labels],
            "reviews": reviews,
            "comments": comments,
            "checks": checks,
            "url": pr.html_url,
        }

    except RateLimitExceededException as exc:
        raise GitHubOpsError(_handle_rate_limit(exc))
    except GithubException as exc:
        raise GitHubOpsError(_safe_error(exc))


def gh_pr_create(
    repo: str,
    title: str,
    body: str,
    head: str,
    base: str = "main",
    labels: list[str] | None = None,
    reviewers: list[str] | None = None,
) -> dict:
    """Create a pull request."""
    client = _get_client()
    try:
        gh_repo = client.get_repo(repo)
        pr = gh_repo.create_pull(title=title, body=body, head=head, base=base)

        if labels:
            pr.set_labels(*labels)
        if reviewers:
            pr.create_review_request(reviewers=reviewers)

        return {
            "number": pr.number,
            "title": pr.title,
            "url": pr.html_url,
            "state": pr.state,
        }

    except RateLimitExceededException as exc:
        raise GitHubOpsError(_handle_rate_limit(exc))
    except GithubException as exc:
        raise GitHubOpsError(_safe_error(exc))


def gh_issues(
    repo: str,
    state: str = "open",
    action: str = "list",
    title: str | None = None,
    body: str | None = None,
    number: int | None = None,
) -> list[dict] | dict:
    """List, create, or update issues."""
    client = _get_client()
    try:
        gh_repo = client.get_repo(repo)

        if action == "list":
            issues = gh_repo.get_issues(state=state, sort="updated", direction="desc")
            results = []
            count = 0
            for issue in issues:
                if count >= 50:
                    break
                count += 1
                if issue.pull_request:
                    continue
                results.append({
                    "number": issue.number,
                    "title": issue.title,
                    "state": issue.state,
                    "author": issue.user.login,
                    "labels": [l.name for l in issue.labels],
                    "created_at": issue.created_at.isoformat(),
                    "updated_at": issue.updated_at.isoformat(),
                    "url": issue.html_url,
                })
            return results

        elif action == "create":
            if not title:
                raise GitHubOpsError("Title is required to create an issue.")
            issue = gh_repo.create_issue(title=title, body=body or "")
            return {
                "number": issue.number,
                "title": issue.title,
                "url": issue.html_url,
                "state": issue.state,
            }

        elif action == "update":
            if number is None:
                raise GitHubOpsError("Issue number is required for update.")
            issue = gh_repo.get_issue(number)
            kwargs = {}
            if title:
                kwargs["title"] = title
            if body:
                kwargs["body"] = body
            issue.edit(**kwargs)
            return {
                "number": issue.number,
                "title": issue.title,
                "url": issue.html_url,
                "state": issue.state,
            }

        else:
            raise GitHubOpsError(
                f"Unknown action: {action}. Use list, create, or update."
            )

    except RateLimitExceededException as exc:
        raise GitHubOpsError(_handle_rate_limit(exc))
    except GithubException as exc:
        raise GitHubOpsError(_safe_error(exc))


def gh_actions(
    repo: str,
    workflow: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """List recent workflow runs."""
    client = _get_client()
    try:
        gh_repo = client.get_repo(repo)

        kwargs = {}
        if status:
            kwargs["status"] = status

        if workflow:
            runs = gh_repo.get_workflow(workflow).get_runs(**kwargs)
        else:
            runs = gh_repo.get_workflow_runs(**kwargs)

        results = []
        count = 0
        for run in runs:
            if count >= 20:
                break
            count += 1
            duration = None
            if run.created_at and run.updated_at:
                duration = (run.updated_at - run.created_at).total_seconds()

            results.append({
                "id": run.id,
                "name": run.name,
                "status": run.status,
                "conclusion": run.conclusion,
                "branch": run.head_branch,
                "event": run.event,
                "created_at": run.created_at.isoformat(),
                "duration_seconds": duration,
                "url": run.html_url,
            })

        return results

    except RateLimitExceededException as exc:
        raise GitHubOpsError(_handle_rate_limit(exc))
    except GithubException as exc:
        raise GitHubOpsError(_safe_error(exc))

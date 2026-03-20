"""Mooring MCP server — Git and GitHub tools via FastMCP."""

import json

from mcp.server.fastmcp import FastMCP

from mooring import __version__
from mooring.git_ops import GitOpsError, repo_status as _repo_status
from mooring.git_ops import repo_log as _repo_log
from mooring.git_ops import repo_diff as _repo_diff
from mooring.git_ops import repo_blame as _repo_blame
from mooring.git_ops import repo_branches as _repo_branches
from mooring.git_ops import repo_stash as _repo_stash
from mooring.github_ops import GitHubOpsError
from mooring.github_ops import gh_pr_list as _gh_pr_list
from mooring.github_ops import gh_pr_detail as _gh_pr_detail
from mooring.github_ops import gh_pr_create as _gh_pr_create
from mooring.github_ops import gh_issues as _gh_issues
from mooring.github_ops import gh_actions as _gh_actions

mcp = FastMCP("Mooring")


def _json(data: object) -> str:
    """Serialize data to formatted JSON string."""
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
def health() -> str:
    """Return server version and status."""
    return _json({"server": "Mooring", "version": __version__, "status": "ok"})


@mcp.tool()
def repo_status(repo_path: str) -> str:
    """Enhanced git status: branch, ahead/behind, stash count, staged/unstaged/untracked files.

    Args:
        repo_path: Path to local git repository.
    """
    try:
        return _json(_repo_status(repo_path))
    except GitOpsError as exc:
        return _json({"error": str(exc)})


@mcp.tool()
def repo_log(
    repo_path: str,
    max_count: int = 20,
    author: str | None = None,
    since: str | None = None,
    path: str | None = None,
    search: str | None = None,
) -> str:
    """Formatted commit log with optional filters.

    Args:
        repo_path: Path to local git repository.
        max_count: Maximum commits to return (default 20).
        author: Filter by author name.
        since: Filter by date (e.g., "2024-01-01").
        path: Filter by file path.
        search: Search commit messages.
    """
    try:
        return _json(_repo_log(repo_path, max_count, author, since, path, search))
    except GitOpsError as exc:
        return _json({"error": str(exc)})


@mcp.tool()
def repo_diff(
    repo_path: str,
    staged: bool = False,
    from_ref: str | None = None,
    to_ref: str | None = None,
) -> str:
    """Unified diff output between refs, staged, or working tree.

    Args:
        repo_path: Path to local git repository.
        staged: Show staged changes (default false).
        from_ref: Starting reference for diff.
        to_ref: Ending reference for diff.
    """
    try:
        return _repo_diff(repo_path, staged, from_ref, to_ref)
    except GitOpsError as exc:
        return _json({"error": str(exc)})


@mcp.tool()
def repo_blame(
    repo_path: str,
    file_path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> str:
    """Git blame with optional line range. File path must be within the repository.

    Args:
        repo_path: Path to local git repository.
        file_path: File path relative to repo root.
        start_line: Starting line number (optional).
        end_line: Ending line number (optional).
    """
    try:
        return _json(_repo_blame(repo_path, file_path, start_line, end_line))
    except GitOpsError as exc:
        return _json({"error": str(exc)})


@mcp.tool()
def repo_branches(repo_path: str) -> str:
    """List all branches with tracking info, last commit, and ahead/behind counts.

    Args:
        repo_path: Path to local git repository.
    """
    try:
        return _json(_repo_branches(repo_path))
    except GitOpsError as exc:
        return _json({"error": str(exc)})


@mcp.tool()
def repo_stash(
    repo_path: str,
    action: str = "list",
    message: str | None = None,
) -> str:
    """Stash operations: list, push, pop, or apply.

    Args:
        repo_path: Path to local git repository.
        action: One of list, push, pop, apply (default list).
        message: Message for stash push (optional).
    """
    try:
        return _json(_repo_stash(repo_path, action, message))
    except GitOpsError as exc:
        return _json({"error": str(exc)})


@mcp.tool()
def gh_pr_list(
    repo: str,
    state: str = "open",
    author: str | None = None,
    label: str | None = None,
) -> str:
    """List pull requests from a GitHub repository.

    Args:
        repo: Repository in owner/name format.
        state: PR state: open, closed, or all (default open).
        author: Filter by PR author login.
        label: Filter by label name.
    """
    try:
        return _json(_gh_pr_list(repo, state, author, label))
    except GitHubOpsError as exc:
        return _json({"error": str(exc)})


@mcp.tool()
def gh_pr_detail(repo: str, number: int) -> str:
    """Get detailed information about a specific pull request.

    Args:
        repo: Repository in owner/name format.
        number: PR number.
    """
    try:
        return _json(_gh_pr_detail(repo, number))
    except GitHubOpsError as exc:
        return _json({"error": str(exc)})


@mcp.tool()
def gh_pr_create(
    repo: str,
    title: str,
    body: str,
    head: str,
    base: str = "main",
    labels: list[str] | None = None,
    reviewers: list[str] | None = None,
) -> str:
    """Create a pull request.

    Args:
        repo: Repository in owner/name format.
        title: PR title.
        body: PR description body.
        head: Source branch name.
        base: Target branch name (default main).
        labels: List of label names to apply.
        reviewers: List of reviewer login names.
    """
    try:
        return _json(_gh_pr_create(repo, title, body, head, base, labels, reviewers))
    except GitHubOpsError as exc:
        return _json({"error": str(exc)})


@mcp.tool()
def gh_issues(
    repo: str,
    state: str = "open",
    action: str = "list",
    title: str | None = None,
    body: str | None = None,
    number: int | None = None,
) -> str:
    """List, create, or update GitHub issues.

    Args:
        repo: Repository in owner/name format.
        state: Issue state: open, closed, or all (default open).
        action: One of list, create, update.
        title: Issue title (required for create).
        body: Issue body (for create or update).
        number: Issue number (required for update).
    """
    try:
        return _json(_gh_issues(repo, state, action, title, body, number))
    except GitHubOpsError as exc:
        return _json({"error": str(exc)})


@mcp.tool()
def gh_actions(
    repo: str,
    workflow: str | None = None,
    status: str | None = None,
) -> str:
    """List recent GitHub Actions workflow runs.

    Args:
        repo: Repository in owner/name format.
        workflow: Filter by workflow name (optional).
        status: Filter by status (optional).
    """
    try:
        return _json(_gh_actions(repo, workflow, status))
    except GitHubOpsError as exc:
        return _json({"error": str(exc)})


def main():
    """Run the Mooring MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()

"""Local git operations using GitPython.

All functions take a repo_path string and return structured data.
No subprocess calls — GitPython API only.
"""

from pathlib import Path

import git


class GitOpsError(Exception):
    """Raised when a git operation fails."""


def _open_repo(repo_path: str) -> git.Repo:
    """Open and validate a git repository path."""
    path = Path(repo_path).resolve()
    if not path.exists():
        raise GitOpsError(f"Path does not exist: {repo_path}")
    if not path.is_dir():
        raise GitOpsError(f"Path is not a directory: {repo_path}")
    try:
        return git.Repo(str(path))
    except git.InvalidGitRepositoryError:
        raise GitOpsError(f"Not a git repository: {repo_path}")


def _validate_file_in_repo(repo: git.Repo, file_path: str) -> Path:
    """Validate that file_path is within the repo working directory.

    Prevents path traversal attacks (e.g., ../../etc/passwd).
    """
    repo_root = Path(repo.working_dir).resolve()
    target = (repo_root / file_path).resolve()
    if not str(target).startswith(str(repo_root)):
        raise GitOpsError(
            f"Path traversal rejected: {file_path} resolves outside the repository"
        )
    if not target.exists():
        raise GitOpsError(f"File does not exist: {file_path}")
    return target


def repo_status(repo_path: str) -> dict:
    """Enhanced git status with branch, tracking, stash, and file lists."""
    repo = _open_repo(repo_path)

    branch_name = repo.active_branch.name if not repo.head.is_detached else "HEAD (detached)"

    # Ahead/behind tracking branch
    ahead, behind = 0, 0
    tracking_branch = None
    try:
        tracking = repo.active_branch.tracking_branch()
        if tracking is not None:
            tracking_branch = tracking.name
            commits_ahead = list(repo.iter_commits(f"{tracking.name}..{repo.active_branch.name}"))
            commits_behind = list(repo.iter_commits(f"{repo.active_branch.name}..{tracking.name}"))
            ahead = len(commits_ahead)
            behind = len(commits_behind)
    except (TypeError, ValueError, git.GitCommandError):
        pass

    # Stash count
    try:
        stash_list = repo.git.stash("list")
        stash_count = len(stash_list.strip().splitlines()) if stash_list.strip() else 0
    except git.GitCommandError:
        stash_count = 0

    # File categories
    staged = []
    unstaged = []
    untracked = list(repo.untracked_files)

    diff_staged = repo.index.diff(repo.head.commit) if not repo.head.is_detached and repo.head.is_valid() else repo.index.diff(None)
    for d in diff_staged:
        staged.append({"path": d.a_path or d.b_path, "change_type": d.change_type})

    diff_unstaged = repo.index.diff(None)
    for d in diff_unstaged:
        unstaged.append({"path": d.a_path or d.b_path, "change_type": d.change_type})

    return {
        "branch": branch_name,
        "tracking_branch": tracking_branch,
        "ahead": ahead,
        "behind": behind,
        "stash_count": stash_count,
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
    }


def repo_log(
    repo_path: str,
    max_count: int = 20,
    author: str | None = None,
    since: str | None = None,
    path: str | None = None,
    search: str | None = None,
) -> list[dict]:
    """Formatted commit log with optional filters."""
    repo = _open_repo(repo_path)

    kwargs: dict = {"max_count": max_count}
    if author:
        kwargs["author"] = author
    if since:
        kwargs["since"] = since

    commits_iter = repo.iter_commits(repo.active_branch.name, **kwargs)

    results = []
    for commit in commits_iter:
        message = commit.message.strip()

        # Filter by path if specified
        if path and path not in commit.stats.files:
            continue

        # Filter by search term in message
        if search and search.lower() not in message.lower():
            continue

        results.append({
            "hash": commit.hexsha,
            "short_hash": commit.hexsha[:7],
            "author": str(commit.author),
            "date": commit.committed_datetime.isoformat(),
            "message": message,
        })

    return results


def repo_diff(
    repo_path: str,
    staged: bool = False,
    from_ref: str | None = None,
    to_ref: str | None = None,
) -> str:
    """Unified diff output."""
    repo = _open_repo(repo_path)

    if from_ref and to_ref:
        return repo.git.diff(from_ref, to_ref)
    elif from_ref:
        return repo.git.diff(from_ref)
    elif staged:
        return repo.git.diff("--cached")
    else:
        return repo.git.diff()


def repo_blame(
    repo_path: str,
    file_path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> list[dict]:
    """Git blame with optional line range."""
    repo = _open_repo(repo_path)
    _validate_file_in_repo(repo, file_path)

    kwargs = {}
    if start_line is not None and end_line is not None:
        kwargs["L"] = f"{start_line},{end_line}"
    elif start_line is not None:
        kwargs["L"] = f"{start_line},"

    blame_entries = repo.blame(repo.active_branch.name, file_path, **kwargs)

    results = []
    line_num = start_line or 1
    for commit, lines in blame_entries:
        for line in lines:
            results.append({
                "line": line_num,
                "content": line,
                "hash": commit.hexsha[:7],
                "author": str(commit.author),
                "date": commit.committed_datetime.isoformat(),
                "message": commit.message.strip(),
            })
            line_num += 1

    return results


def repo_branches(repo_path: str) -> list[dict]:
    """List all branches with tracking info."""
    repo = _open_repo(repo_path)
    current = repo.active_branch.name if not repo.head.is_detached else None

    branches = []
    for branch in repo.branches:
        last_commit = branch.commit
        tracking = None
        ahead, behind = 0, 0

        try:
            tb = branch.tracking_branch()
            if tb is not None:
                tracking = tb.name
                ahead = len(list(repo.iter_commits(f"{tb.name}..{branch.name}")))
                behind = len(list(repo.iter_commits(f"{branch.name}..{tb.name}")))
        except (TypeError, ValueError, git.GitCommandError):
            pass

        branches.append({
            "name": branch.name,
            "is_current": branch.name == current,
            "last_commit_date": last_commit.committed_datetime.isoformat(),
            "last_commit_message": last_commit.message.strip(),
            "tracking_branch": tracking,
            "ahead": ahead,
            "behind": behind,
        })

    return branches


def repo_stash(
    repo_path: str,
    action: str = "list",
    message: str | None = None,
) -> dict:
    """Stash operations: list, push, pop, apply."""
    repo = _open_repo(repo_path)

    if action == "list":
        output = repo.git.stash("list")
        entries = output.strip().splitlines() if output.strip() else []
        return {"action": "list", "entries": entries, "count": len(entries)}

    elif action == "push":
        args = ["push"]
        if message:
            args.extend(["-m", message])
        output = repo.git.stash(*args)
        return {"action": "push", "result": output}

    elif action == "pop":
        output = repo.git.stash("pop")
        return {"action": "pop", "result": output}

    elif action == "apply":
        output = repo.git.stash("apply")
        return {"action": "apply", "result": output}

    else:
        raise GitOpsError(f"Unknown stash action: {action}. Use list, push, pop, or apply.")

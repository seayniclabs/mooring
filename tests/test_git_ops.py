"""Tests for local git operations using conftest fixtures."""

import pytest

from mooring.git_ops import (
    GitOpsError,
    repo_blame,
    repo_branches,
    repo_diff,
    repo_log,
    repo_stash,
    repo_status,
)


class TestRepoStatus:
    def test_clean_repo(self, test_repo):
        result = repo_status(test_repo.working_dir)
        assert result["branch"] == "main"
        assert result["staged"] == []
        assert result["unstaged"] == []
        assert result["untracked"] == []
        assert result["stash_count"] == 0

    def test_dirty_repo(self, dirty_repo):
        result = repo_status(dirty_repo.working_dir)
        assert result["branch"] == "main"
        # README.md was modified
        unstaged_paths = [f["path"] for f in result["unstaged"]]
        assert "README.md" in unstaged_paths
        # untracked.txt was added
        assert "untracked.txt" in result["untracked"]

    def test_invalid_path(self, tmp_path):
        with pytest.raises(GitOpsError, match="Not a git repository"):
            repo_status(str(tmp_path))

    def test_nonexistent_path(self):
        with pytest.raises(GitOpsError, match="does not exist"):
            repo_status("/nonexistent/path")

    def test_file_not_directory(self, test_repo, tmp_path):
        f = tmp_path / "afile.txt"
        f.write_text("hello")
        with pytest.raises(GitOpsError, match="not a directory"):
            repo_status(str(f))

    def test_staged_files(self, test_repo):
        from pathlib import Path
        workdir = Path(test_repo.working_dir)
        (workdir / "staged.txt").write_text("new\n")
        test_repo.index.add(["staged.txt"])
        result = repo_status(test_repo.working_dir)
        staged_paths = [f["path"] for f in result["staged"]]
        assert "staged.txt" in staged_paths


class TestRepoLog:
    def test_returns_commits(self, test_repo):
        result = repo_log(test_repo.working_dir)
        assert len(result) >= 2
        messages = [c["message"] for c in result]
        assert "Add main module" in messages
        assert "Initial commit" in messages

    def test_max_count(self, test_repo):
        result = repo_log(test_repo.working_dir, max_count=1)
        assert len(result) == 1

    def test_author_filter(self, test_repo):
        result = repo_log(test_repo.working_dir, author="Test User")
        assert len(result) >= 1
        for commit in result:
            assert commit["author"] == "Test User"

    def test_author_filter_no_match(self, test_repo):
        result = repo_log(test_repo.working_dir, author="Nobody")
        assert len(result) == 0

    def test_search_filter(self, test_repo):
        result = repo_log(test_repo.working_dir, search="Initial")
        assert len(result) == 1
        assert result[0]["message"] == "Initial commit"

    def test_since_filter(self, test_repo):
        # All commits should be recent
        result = repo_log(test_repo.working_dir, since="2020-01-01")
        assert len(result) >= 1

    def test_path_filter(self, test_repo):
        result = repo_log(test_repo.working_dir, path="src/main.py")
        assert len(result) == 1
        assert result[0]["message"] == "Add main module"

    def test_path_filter_no_match(self, test_repo):
        result = repo_log(test_repo.working_dir, path="nonexistent.py")
        assert len(result) == 0

    def test_commit_fields(self, test_repo):
        result = repo_log(test_repo.working_dir, max_count=1)
        commit = result[0]
        assert "hash" in commit
        assert "short_hash" in commit
        assert "author" in commit
        assert "date" in commit
        assert "message" in commit
        assert len(commit["short_hash"]) == 7


class TestRepoDiff:
    def test_diff_between_branches(self, test_repo):
        result = repo_diff(
            test_repo.working_dir,
            from_ref="main",
            to_ref="feature/add-tests",
        )
        assert "test_main.py" in result

    def test_clean_working_tree(self, test_repo):
        result = repo_diff(test_repo.working_dir)
        assert result == ""

    def test_dirty_working_tree(self, dirty_repo):
        result = repo_diff(dirty_repo.working_dir)
        assert "Modified" in result

    def test_staged_diff(self, test_repo):
        from pathlib import Path
        workdir = Path(test_repo.working_dir)
        (workdir / "new.txt").write_text("staged content\n")
        test_repo.index.add(["new.txt"])
        result = repo_diff(test_repo.working_dir, staged=True)
        assert "staged content" in result

    def test_from_ref_only(self, test_repo):
        result = repo_diff(test_repo.working_dir, from_ref="HEAD~1")
        assert "main.py" in result


class TestRepoBlame:
    def test_blame_readme(self, test_repo):
        result = repo_blame(test_repo.working_dir, "README.md")
        assert len(result) > 0
        assert result[0]["line"] == 1
        assert result[0]["author"] == "Test User"
        assert "content" in result[0]

    def test_path_traversal_rejected(self, test_repo):
        with pytest.raises(GitOpsError, match="Path traversal rejected"):
            repo_blame(test_repo.working_dir, "../../etc/passwd")

    def test_nonexistent_file(self, test_repo):
        with pytest.raises(GitOpsError, match="does not exist"):
            repo_blame(test_repo.working_dir, "nonexistent.txt")

    def test_blame_with_line_range(self, test_repo):
        result = repo_blame(test_repo.working_dir, "README.md", start_line=1, end_line=2)
        assert len(result) == 2
        assert result[0]["line"] == 1
        assert result[1]["line"] == 2

    def test_blame_with_start_line_only(self, test_repo):
        result = repo_blame(test_repo.working_dir, "README.md", start_line=2)
        assert len(result) >= 1
        assert result[0]["line"] == 2


class TestRepoBranches:
    def test_lists_branches(self, test_repo):
        result = repo_branches(test_repo.working_dir)
        names = [b["name"] for b in result]
        assert "main" in names
        assert "feature/add-tests" in names

    def test_current_branch(self, test_repo):
        result = repo_branches(test_repo.working_dir)
        current = [b for b in result if b["is_current"]]
        assert len(current) == 1
        assert current[0]["name"] == "main"

    def test_branch_fields(self, test_repo):
        result = repo_branches(test_repo.working_dir)
        branch = result[0]
        assert "name" in branch
        assert "is_current" in branch
        assert "last_commit_date" in branch
        assert "last_commit_message" in branch
        assert "tracking_branch" in branch
        assert "ahead" in branch
        assert "behind" in branch


class TestRepoStash:
    def test_stash_empty(self, test_repo):
        result = repo_stash(test_repo.working_dir, action="list")
        assert result["count"] == 0
        assert result["entries"] == []

    def test_stash_push_list_pop(self, dirty_repo):
        # Push a stash
        push_result = repo_stash(dirty_repo.working_dir, action="push", message="test stash")
        assert push_result["action"] == "push"

        # List shows one stash
        list_result = repo_stash(dirty_repo.working_dir, action="list")
        assert list_result["count"] == 1
        assert "test stash" in list_result["entries"][0]

        # Pop restores it
        pop_result = repo_stash(dirty_repo.working_dir, action="pop")
        assert pop_result["action"] == "pop"

        # List is empty again
        list_result = repo_stash(dirty_repo.working_dir, action="list")
        assert list_result["count"] == 0

    def test_stash_apply(self, dirty_repo):
        repo_stash(dirty_repo.working_dir, action="push", message="apply test")
        apply_result = repo_stash(dirty_repo.working_dir, action="apply")
        assert apply_result["action"] == "apply"
        # Stash still exists after apply (unlike pop)
        list_result = repo_stash(dirty_repo.working_dir, action="list")
        assert list_result["count"] == 1

    def test_invalid_action(self, test_repo):
        with pytest.raises(GitOpsError, match="Unknown stash action"):
            repo_stash(test_repo.working_dir, action="invalid")

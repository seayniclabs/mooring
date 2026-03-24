"""Mooring MCP server test fixtures.

Creates throwaway git repos with known history for integration testing.
GitHub API calls are mocked — no real token needed for CI.
"""

import os
from pathlib import Path

import pytest

# Only import git when tests actually need it
try:
    import git
except ImportError:
    git = None


@pytest.fixture
def test_repo(tmp_path):
    """Create a throwaway git repo with branches and history."""
    assert git is not None, "GitPython is required: pip install gitpython"

    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()
    repo = git.Repo.init(repo_path, initial_branch="main")

    # Configure git user for commits
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@test.local").release()

    # Initial commit on main
    readme = repo_path / "README.md"
    readme.write_text("# Test Repository\n\nCreated for Mooring integration tests.\n")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    # Second commit on main
    src_dir = repo_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text('def main():\n    print("hello")\n')
    repo.index.add(["src/main.py"])
    repo.index.commit("Add main module")

    # Feature branch with changes
    feature = repo.create_head("feature/add-tests")
    feature.checkout()

    tests_dir = repo_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_main.py").write_text(
        'def test_main():\n    assert True\n'
    )
    repo.index.add(["tests/test_main.py"])
    repo.index.commit("Add test file")

    # Back to main
    repo.heads.main.checkout()

    return repo


@pytest.fixture
def dirty_repo(test_repo):
    """A repo with uncommitted changes."""
    workdir = Path(test_repo.working_dir)
    (workdir / "README.md").write_text("# Modified\n")
    (workdir / "untracked.txt").write_text("new file\n")
    return test_repo


@pytest.fixture
def detached_repo(test_repo):
    """A repo in detached HEAD state (checked out to a specific commit hash)."""
    commit_sha = test_repo.head.commit.hexsha
    test_repo.head.reference = test_repo.head.commit
    # Detach HEAD by checking out the commit directly
    test_repo.git.checkout(commit_sha)
    assert test_repo.head.is_detached
    return test_repo


@pytest.fixture
def mock_github_token(monkeypatch):
    """Set a fake GitHub token for tests that check auth."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_FAKE_TOKEN_FOR_TESTING_ONLY")


@pytest.fixture
def no_github_token(monkeypatch):
    """Ensure no GitHub token is set."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

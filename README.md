# Mooring — Git & GitHub MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-FB7185.svg)](LICENSE)

Mooring lines for your code — Git and GitHub operations for AI tools.

Mooring is an [MCP](https://modelcontextprotocol.io/) server that gives AI assistants structured access to local Git repositories and the GitHub API. Local operations use GitPython (no subprocess calls). GitHub operations use the PyGithub library with token masking and rate limit handling built in.

---

## Tools

### Local Git

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `repo_status` | Branch, ahead/behind, stash count, staged/unstaged/untracked files | `repo_path` |
| `repo_log` | Commit log with optional filters | `repo_path`, `max_count`, `author`, `since`, `path`, `search` |
| `repo_diff` | Unified diff — working tree, staged, or between refs | `repo_path`, `staged`, `from_ref`, `to_ref` |
| `repo_blame` | Git blame with optional line range | `repo_path`, `file_path`, `start_line`, `end_line` |
| `repo_branches` | All branches with tracking info, last commit, ahead/behind | `repo_path` |
| `repo_stash` | Stash operations: list, push, pop, apply | `repo_path`, `action`, `message` |

### GitHub

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `gh_pr_list` | List pull requests | `repo`, `state`, `author`, `label` |
| `gh_pr_detail` | PR detail with reviews, comments, and check runs | `repo`, `number` |
| `gh_pr_create` | Create a pull request | `repo`, `title`, `body`, `head`, `base`, `labels`, `reviewers` |
| `gh_issues` | List, create, or update issues | `repo`, `state`, `action`, `title`, `body`, `number` |
| `gh_actions` | List recent GitHub Actions workflow runs | `repo`, `workflow`, `status` |

### Utility

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `health` | Server version and status check | _(none)_ |

---

## Installation

```bash
# PyPI
pip install mooring-mcp

# Isolated install
pipx install mooring-mcp
```

---

## Usage

Run the server directly:

```bash
mooring
```

### Claude Code

```bash
claude mcp add mooring -- mooring
```

### Claude Desktop

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mooring": {
      "command": "mooring",
      "env": {
        "GITHUB_TOKEN": "your-github-personal-access-token"
      }
    }
  }
}
```

The `GITHUB_TOKEN` environment variable is required for all GitHub tools (`gh_*`). Local Git tools work without it.

---

## Security

- **Path traversal protection** — file paths are resolved and validated against the repository root before any operation
- **Symlink escape detection** — symlinks that resolve outside the repository are rejected
- **Ref validation** — Git refs are checked against a safe character pattern and verified to exist before use
- **Token masking** — error messages are scrubbed for GitHub token patterns (`ghp_*`, `gho_*`, `github_pat_*`) before being returned
- **Rate limit handling** — GitHub 403 responses are caught and surfaced as clear messages instead of raw exceptions

---

## Development

```bash
git clone https://github.com/seayniclabs/mooring.git
cd mooring
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
python -m pytest tests/ -q
```

---

## License

[MIT](LICENSE)

<!-- mcp-name: io.github.seayniclabs/mooring -->

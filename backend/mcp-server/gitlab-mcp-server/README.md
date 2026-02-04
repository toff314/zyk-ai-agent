# GitLab MCP Server

A read-only MCP server for GitLab that lists projects, users, commits, and commit diffs.

## Features
- list_projects
- list_users
- list_commits
- get_commit_diff

## Setup

```bash
pip install python-gitlab fastmcp python-dotenv
```

Create `.env` from `.env.example` and fill in credentials.

## Run

```bash
python server.py
```

## Claude Desktop example

```json
{
  "mcpServers": {
    "gitlab": {
      "command": "python",
      "args": ["/path/to/gitlab-mcp-server/server.py"],
      "env": {
        "GITLAB_URL": "https://gitlab.example.com",
        "GITLAB_TOKEN": "your_token_here",
        "GITLAB_GROUPS": "group-a,group-b"
      }
    }
  }
}
```

## Tool examples

- list projects: "List GitLab projects"
- list users: "List GitLab users"
- list commits: "List commits for project 123 (limit 10)"
- commit diff: "Get commit diff for project 123, sha abc123"

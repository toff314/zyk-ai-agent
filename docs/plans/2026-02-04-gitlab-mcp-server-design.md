# GitLab MCP Server Design

## Goal
Build a GitLab MCP server that exposes four read-only tools: list projects, list users, list recent commits for a project, and fetch a commit diff (patch text). Configuration comes from a local `.env` file.

## Architecture
The server lives at `backend/mcp-server/gitlab-mcp-server` and follows the existing MySQL MCP server pattern. It uses `fastmcp` for tool registration, `python-gitlab` for API access, and `python-dotenv` for loading environment variables. A small connection helper caches the GitLab client to avoid re-authentication per request. Pagination is explicit to avoid unbounded `all=True` calls.

## Data Flow
Each tool loads configuration from environment variables (`GITLAB_URL`, `GITLAB_TOKEN`, optional `GITLAB_GROUPS`, `GITLAB_API_VERSION`, `GITLAB_PER_PAGE`, `GITLAB_MAX_DIFF_CHARS`) and uses the GitLab client to query data. For list projects, if `GITLAB_GROUPS` is set, the server fetches projects within those groups; otherwise it lists all visible projects. Commit listing returns a bounded number of recent commits. Commit diff returns commit metadata plus file-level patches, truncated to a maximum size.

## Error Handling
All API calls are wrapped with clear exceptions that point to likely causes (auth failure, missing configuration, or not found). Logging is sent to stderr to avoid interfering with JSON-RPC output. Invalid parameters (non-positive limits, empty commit SHA) are rejected with explicit errors. If configured groups are missing, the server returns an empty list rather than crashing.

## Testing & Documentation
Tests are lightweight and local to the MCP server directory. They validate configuration parsing, limit clamping, diff truncation, and tool output formatting using stubbed GitLab objects to avoid network access. A `README.md` documents setup, environment variables, and usage examples. A `.env.example` provides a reference configuration. A `test_connection.py` script can be used to verify access to GitLab with real credentials.

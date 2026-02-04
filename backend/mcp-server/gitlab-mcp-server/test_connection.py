#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    import gitlab

    print("=" * 50)
    print("GitLab MCP Server connection test")
    print("=" * 50)

    url = os.getenv("GITLAB_URL")
    token = os.getenv("GITLAB_TOKEN")
    if not url or not token:
        raise Exception("Missing GITLAB_URL or GITLAB_TOKEN")

    gl = gitlab.Gitlab(
        url=url,
        private_token=token,
        api_version=os.getenv("GITLAB_API_VERSION", "4"),
    )
    gl.auth()

    user = gl.user
    print("Connected as:", user.username)
    print("OK")
except Exception as exc:
    print("Connection failed:", exc)
    sys.exit(1)

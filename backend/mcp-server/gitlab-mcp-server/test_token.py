#!/usr/bin/env python3
"""Minimal GitLab token check (URL + token via args)."""
import sys

import gitlab


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: test_token.py <gitlab_url> <token>")
        print("Example: test_token.py https://gitlab.example.com glpat-xxxx")
        return 2

    url = sys.argv[1].strip()
    token = sys.argv[2].strip()
    if not url or not token:
        print("ERROR: url and token are required")
        return 2

    try:
        gl = gitlab.Gitlab(url=url, private_token=token, api_version="4")
        gl.auth()
        user = gl.user
        print(f"OK: {user.username} ({user.name})")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

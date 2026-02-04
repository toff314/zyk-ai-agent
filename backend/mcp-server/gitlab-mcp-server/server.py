import logging
import os
import sys
from typing import List, Optional

from dotenv import load_dotenv
import gitlab
from fastmcp import FastMCP

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)

load_dotenv()

mcp = FastMCP("GitLab MCP Server")

DEFAULT_LIMIT = 20
MAX_LIMIT = 200


def _parse_groups(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _clamp_limit(limit: Optional[int]) -> int:
    if limit is None or limit <= 0:
        return DEFAULT_LIMIT
    return min(limit, MAX_LIMIT)


def _truncate_patch(patch: Optional[str], max_chars: int) -> str:
    if not patch or max_chars <= 0:
        return ""
    if len(patch) <= max_chars:
        return patch
    return patch[:max_chars] + "... [truncated]"


if __name__ == "__main__":
    mcp.run()

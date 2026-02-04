"""
MCP GitLab工具服务
"""
import subprocess
import sys
import json
import mcp.types as mcp_types
from typing import Optional, Any
from pathlib import Path
import logging
import select as select_module
import time

from sqlalchemy import select as sa_select

from app.models.database import get_db
from app.models.gitlab_project import GitLabProject

from app.config.settings import settings

logger = logging.getLogger(__name__)


class MCPGitLabClient:
    """MCP GitLab客户端"""

    def __init__(self):
        backend_root = Path(__file__).resolve().parents[2]
        self.server_path = str(backend_root / "mcp-server" / "gitlab-mcp-server" / "server.py")
        self._request_id = 0

    def _build_env(self, gitlab_config: Optional[dict[str, Any]] = None) -> dict[str, str]:
        env = {}
        if gitlab_config:
            env.update({
                "GITLAB_URL": gitlab_config.get("url", ""),
                "GITLAB_TOKEN": gitlab_config.get("token", ""),
                "GITLAB_GROUPS": gitlab_config.get("groups", ""),
            })
        else:
            env.update({
                "GITLAB_URL": settings.GITLAB_URL,
                "GITLAB_TOKEN": settings.GITLAB_TOKEN,
            })
        return env

    def _call_tool(
        self,
        name: str,
        arguments: Optional[dict[str, Any]],
        gitlab_config: Optional[dict[str, Any]] = None,
    ) -> list[dict]:
        self._request_id += 1
        init_id = self._request_id
        self._request_id += 1
        call_id = self._request_id

        init_request = {
            "jsonrpc": "2.0",
            "id": init_id,
            "method": "initialize",
            "params": {
                "protocolVersion": mcp_types.LATEST_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "zyk-ai-agent", "version": "0.1"},
            },
        }
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
        call_request = {
            "jsonrpc": "2.0",
            "id": call_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }

        process = subprocess.Popen(
            [sys.executable, self.server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self._build_env(gitlab_config),
        )
        input_text = "\n".join(
            json.dumps(item, ensure_ascii=False)
            for item in [init_request, initialized_notification, call_request]
        ) + "\n"
        if not process.stdin or not process.stdout or not process.stderr:
            process.kill()
            raise Exception("MCP Server failed to start with stdio pipes")

        process.stdin.write(input_text)
        process.stdin.flush()

        response = None
        responses = []
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        deadline = time.time() + float(settings.GITLAB_MCP_TIMEOUT or 120)

        while time.time() < deadline:
            if response is not None:
                break
            if process.poll() is not None:
                break
            rlist, _, _ = select_module.select([process.stdout, process.stderr], [], [], 0.5)
            if not rlist:
                continue
            for stream in rlist:
                line = stream.readline()
                if not line:
                    continue
                if stream is process.stdout:
                    stdout_lines.append(line)
                    try:
                        item = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue
                    responses.append(item)
                    if isinstance(item, dict) and item.get("id") == call_id:
                        response = item
                        break
                else:
                    stderr_lines.append(line)
            if response is not None:
                break

        try:
            process.stdin.close()
        except Exception:
            pass

        try:
            remaining_out, remaining_err = process.communicate(timeout=1)
            if remaining_out:
                stdout_lines.append(remaining_out)
            if remaining_err:
                stderr_lines.append(remaining_err)
        except subprocess.TimeoutExpired:
            process.kill()
            remaining_out, remaining_err = process.communicate()
            if remaining_out:
                stdout_lines.append(remaining_out)
            if remaining_err:
                stderr_lines.append(remaining_err)

        stdout = "".join(stdout_lines)
        stderr = "".join(stderr_lines)

        if stdout:
            logger.info("MCP Server stdout (%s): %s", name, stdout.strip())
        if stderr:
            logger.warning("MCP Server stderr (%s): %s", name, stderr.strip())

        if process.returncode not in (0, None):
            raise Exception(f"MCP Server Error: {stderr}")

        if response is None:
            for item in responses:
                if isinstance(item, dict) and item.get("id") == call_id:
                    response = item
                    break

        if response is None:
            try:
                response = json.loads(stdout)
            except json.JSONDecodeError:
                response = responses[0] if responses else None

        if not isinstance(response, dict):
            raise Exception(f"MCP Server returned no valid response: {stdout}")

        if "error" in response:
            raise Exception(f"Tool Error: {response['error']}")

        return self._parse_tool_result(response)

    def _parse_tool_result(self, response: dict[str, Any]) -> list[dict]:
        result = response.get("result")
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            if result.get("isError") is True:
                content = result.get("content")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            raise Exception(block.get("text", "MCP tool error"))
                raise Exception("MCP tool error")
            if isinstance(result.get("content"), list) and not result.get("content"):
                logger.info("MCP tool returned empty content list.")
                return []
            structured = result.get("structuredContent")
            if structured is not None:
                if isinstance(structured, dict) and "result" in structured:
                    if isinstance(structured["result"], list):
                        return structured["result"]
                return structured
            if "result" in result and isinstance(result["result"], list):
                return result["result"]
            content = result.get("content")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")
                        try:
                            return json.loads(text)
                        except json.JSONDecodeError as exc:
                            raise Exception(f"Unexpected tool result text: {text}") from exc
        raise Exception(f"Unexpected MCP tool result: {result}")

    async def _load_project_ids_from_db(self) -> list[int]:
        db_gen = get_db()
        db = await db_gen.__anext__()
        try:
            result = await db.execute(sa_select(GitLabProject.id))
            return [value for value in result.scalars().all() if value is not None]
        finally:
            try:
                await db_gen.aclose()
            except Exception:
                pass

    async def list_users(self, gitlab_config: Optional[dict[str, Any]] = None) -> list[dict]:
        try:
            return self._call_tool("list_users", {}, gitlab_config=gitlab_config)
        except Exception as e:
            raise Exception(f"获取GitLab用户列表失败: {e}")

    async def list_projects(self, gitlab_config: Optional[dict[str, Any]] = None) -> list[dict]:
        try:
            return self._call_tool("list_projects", {}, gitlab_config=gitlab_config)
        except Exception as e:
            raise Exception(f"获取GitLab项目列表失败: {e}")

    async def list_branches(
        self,
        gitlab_config: Optional[dict[str, Any]],
        project_id: int,
    ) -> list[dict]:
        try:
            return self._call_tool(
                "list_branches",
                {"project_id": project_id},
                gitlab_config=gitlab_config,
            )
        except Exception as e:
            raise Exception(f"获取GitLab分支列表失败: {e}")

    async def list_commits(
        self,
        gitlab_config: Optional[dict[str, Any]],
        project_id: int,
        limit: int = 20,
        ref_name: Optional[str] = None,
    ) -> list[dict]:
        try:
            args: dict[str, Any] = {"project_id": project_id, "limit": limit}
            if ref_name:
                args["ref_name"] = ref_name
            return self._call_tool("list_commits", args, gitlab_config=gitlab_config)
        except Exception as e:
            raise Exception(f"获取GitLab提交列表失败: {e}")

    async def get_user_commits(
        self,
        gitlab_config: Optional[dict[str, Any]],
        username: str,
        limit: int = 10,
        project_ids: Optional[list[int]] = None,
    ) -> list[dict]:
        try:
            if project_ids is None:
                project_ids = await self._load_project_ids_from_db()
                if project_ids:
                    logger.info("MCP get_user_commits uses cached project_ids: %s", len(project_ids))
                else:
                    projects = await self.list_projects(gitlab_config)
                    project_ids = [
                        int(item.get("id"))
                        for item in projects
                        if item.get("id") is not None
                    ]
            if not project_ids:
                logger.warning("MCP get_user_commits has no project_ids")
            result = self._call_tool(
                "get_user_commits",
                {
                    "username": username,
                    "limit": limit,
                    "project_ids": project_ids,
                },
                gitlab_config=gitlab_config,
            )
            if not result:
                logger.warning(
                    "MCP get_user_commits empty result: username=%s limit=%s",
                    username,
                    limit,
                )
            return result
        except Exception as e:
            raise Exception(f"获取GitLab用户提交失败: {e}")

    async def get_commit_diff(
        self,
        gitlab_config: Optional[dict[str, Any]],
        project_id: int,
        commit_sha: str,
    ) -> dict:
        try:
            result = self._call_tool(
                "get_commit_diff",
                {"project_id": project_id, "commit_sha": commit_sha},
                gitlab_config=gitlab_config,
            )
            if isinstance(result, list) and result:
                return result[0]
            if isinstance(result, dict):
                return result
            return {"diffs": []}
        except Exception as e:
            raise Exception(f"获取GitLab提交差异失败: {e}")

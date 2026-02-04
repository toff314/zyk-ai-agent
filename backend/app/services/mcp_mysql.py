"""
MCP MySQL工具服务
"""
import subprocess
import sys
import json
import mcp.types as mcp_types
from typing import Optional, Any
from pathlib import Path
from app.config.settings import settings
import logging
import select
import time

logger = logging.getLogger(__name__)


class MCPMySQLClient:
    """MCP MySQL客户端"""
    
    def __init__(self):
        """初始化客户端"""
        # 基于当前文件位置计算 MCP Server 绝对路径，避免工作目录差异
        backend_root = Path(__file__).resolve().parents[2]
        self.server_path = str(backend_root / "mcp-server" / "mysql-mcp-server" / "server.py")
        self._request_id = 0

    def _build_env(self, mysql_config: Optional[dict[str, Any]] = None) -> dict[str, str]:
        """构建环境变量，优先使用传入的mysql_config"""
        env = {}
        if mysql_config:
            logger.info(f"使用传入的MySQL配置连接: {mysql_config.get('host')}:{mysql_config.get('port')}")
            env.update({
                "MYSQL_HOST": mysql_config.get("host", "localhost"),
                "MYSQL_PORT": str(mysql_config.get("port", 3306)),
                "MYSQL_USER": mysql_config.get("user", ""),
                "MYSQL_PASSWORD": mysql_config.get("password", ""),
                "MYSQL_DATABASE": mysql_config.get("database", ""),
            })
        else:
            logger.info("使用settings默认MySQL配置连接")
            env.update({
                "MYSQL_HOST": settings.MYSQL_HOST,
                "MYSQL_PORT": str(settings.MYSQL_PORT),
                "MYSQL_USER": settings.MYSQL_USER,
                "MYSQL_PASSWORD": settings.MYSQL_PASSWORD,
                "MYSQL_DATABASE": settings.MYSQL_DATABASE,
            })
        return env

    def _call_tool(self, name: str, arguments: Optional[dict[str, Any]], mysql_config: Optional[dict[str, Any]] = None) -> list[dict]:
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
                "clientInfo": {
                    "name": "zyk-ai-agent",
                    "version": "0.1"
                }
            }
        }
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        call_request = {
            "jsonrpc": "2.0",
            "id": call_id,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments or {}
            }
        }

        process = subprocess.Popen(
            [sys.executable, self.server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self._build_env(mysql_config)
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
        deadline = time.time() + 60

        while time.time() < deadline:
            if response is not None:
                break
            if process.poll() is not None:
                break
            rlist, _, _ = select.select([process.stdout, process.stderr], [], [], 0.5)
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
            logger.info("MCP Server stdout: %s", stdout.strip())
        if stderr:
            logger.warning("MCP Server stderr: %s", stderr.strip())

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
    
    async def execute_query(self, query: str, mysql_config: Optional[dict[str, Any]] = None) -> list[dict]:
        """
        执行MySQL查询
        
        参数:
            query: SQL查询语句
        
        返回:
            list[dict]: 查询结果
        """
        try:
            return self._call_tool(
                "execute_query",
                {"sql": query},
                mysql_config=mysql_config
            )
            
        except subprocess.TimeoutExpired:
            process.kill()
            raise Exception("Query timeout")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse response: {e}")
        except Exception as e:
            raise Exception(f"Failed to execute query: {e}")
    
    async def get_hospital_stats(self) -> list[dict]:
        """
        获取医院统计信息
        
        返回:
            list[dict]: 医院统计列表
        """
        query = """
        SELECT 
            institution_name,
            COUNT(*) as total_orders,
            SUM(`total_price`) as total_amount,
            COUNT(DISTINCT patient_id) as patient_count
        FROM order_info
        GROUP BY institution_name
        ORDER BY total_orders DESC
        """
        return await self.execute_query(query)

    async def list_databases(self, mysql_config: Optional[dict[str, Any]] = None) -> list[dict]:
        """列出所有数据库"""
        try:
            databases = self._call_tool("list_databases", {}, mysql_config=mysql_config)
            if not databases:
                fallback_db = (mysql_config or {}).get("database")
                if fallback_db:
                    return [{"database": fallback_db}]
            return databases
        except Exception as e:
            raise Exception(f"获取数据库列表失败: {e}")

    async def list_tables(self, database: Optional[str] = None, mysql_config: Optional[dict[str, Any]] = None) -> list[dict]:
        """列出指定数据库的所有表"""
        try:
            args = {"database": database} if database else {}
            return self._call_tool("list_tables", args, mysql_config=mysql_config)
        except Exception as e:
            raise Exception(f"获取表列表失败: {e}")

    async def describe_table(
        self,
        table_name: str,
        database: Optional[str] = None,
        mysql_config: Optional[dict[str, Any]] = None,
    ) -> list[dict]:
        """获取表结构信息"""
        try:
            args = {"table_name": table_name}
            if database:
                args["database"] = database
            return self._call_tool("describe_table", args, mysql_config=mysql_config)
        except Exception as e:
            raise Exception(f"获取表结构失败: {e}")

    async def show_table_status(
        self,
        database: Optional[str] = None,
        mysql_config: Optional[dict[str, Any]] = None,
    ) -> list[dict]:
        """获取表状态信息"""
        try:
            args = {"database": database} if database else {}
            return self._call_tool("show_table_status", args, mysql_config=mysql_config)
        except Exception as e:
            raise Exception(f"获取表状态失败: {e}")

    async def get_table_indexes(
        self,
        table_name: str,
        database: Optional[str] = None,
        mysql_config: Optional[dict[str, Any]] = None,
    ) -> list[dict]:
        """获取表索引信息"""
        try:
            args = {"table_name": table_name}
            if database:
                args["database"] = database
            return self._call_tool("get_table_indexes", args, mysql_config=mysql_config)
        except Exception as e:
            raise Exception(f"获取索引信息失败: {e}")
    
    async def get_medicine_stats(self) -> list[dict]:
        """
        获取药品消耗统计
        
        返回:
            list[dict]: 药品统计列表
        """
        query = """
        SELECT 
            drug_name,
            SUM(quantity) as total_quantity,
            SUM(quantity * sale_price) as total_cost,
            COUNT(DISTINCT order_id) as order_count
        FROM order_item
        GROUP BY drug_name
        ORDER BY total_quantity DESC
        LIMIT 20
        """
        return await self.execute_query(query)
    
    async def get_order_trends(self, days: int = 7) -> list[dict]:
        """
        获取订单趋势
        
        参数:
            days: 查询天数
        
        返回:
            list[dict]: 订单趋势数据
        """
        query = f"""
        SELECT 
            DATE(create_time) as date,
            COUNT(*) as order_count,
            SUM(`total_price`) as total_amount
        FROM order_info
        WHERE create_time >= DATE_SUB(CURDATE(), INTERVAL {days} DAY)
        GROUP BY DATE(create_time)
        ORDER BY date ASC
        """
        return await self.execute_query(query)
    
    async def get_employee_stats(self) -> list[dict]:
        """
        获取员工工作统计
        
        返回:
            list[dict]: 员工统计列表
        """
        query = """
        SELECT 
            operator_name,
            COUNT(*) as processed_orders,
            SUM(`total_price`) as total_amount
        FROM order_info
        WHERE `status` = 3
        GROUP BY operator_name
        ORDER BY processed_orders DESC
        """
        return await self.execute_query(query)


# 创建全局客户端实例
mcp_mysql_client = MCPMySQLClient()

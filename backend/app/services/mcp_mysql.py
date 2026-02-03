"""
MCP MySQL工具服务
"""
import subprocess
import sys
import json
from typing import Optional, Any
from app.config.settings import settings


class MCPMySQLClient:
    """MCP MySQL客户端"""
    
    def __init__(self):
        """初始化客户端"""
        # 修正 MCP Server 路径（相对于当前工作目录）
        self.server_path = "backend/mcp-server/mysql-mcp-server/server.py"
        self.env = {
            "MYSQL_HOST": settings.MYSQL_HOST,
            "MYSQL_PORT": str(settings.MYSQL_PORT),
            "MYSQL_USER": settings.MYSQL_USER,
            "MYSQL_PASSWORD": settings.MYSQL_PASSWORD,
            "MYSQL_DATABASE": settings.MYSQL_DATABASE,
        }
    
    async def execute_query(self, query: str) -> list[dict]:
        """
        执行MySQL查询
        
        参数:
            query: SQL查询语句
        
        返回:
            list[dict]: 查询结果
        """
        try:
            # 准备输入数据
            input_data = {
                "method": "tools/call",
                "params": {
                    "name": "execute_query",
                    "arguments": {
                        "query": query
                    }
                }
            }
            
            # 执行MCP服务器（使用当前Python解释器）
            process = subprocess.Popen(
                [sys.executable, self.server_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.env
            )
            
            # 发送请求
            process.stdin.write(json.dumps(input_data) + "\n")
            process.stdin.flush()
            
            # 读取响应
            stdout, stderr = process.communicate(timeout=60)
            
            if process.returncode != 0:
                raise Exception(f"MCP Server Error: {stderr}")
            
            # 解析响应
            result = json.loads(stdout)
            
            if "error" in result:
                raise Exception(f"Query Error: {result['error']}")
            
            return result.get("result", [])
            
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

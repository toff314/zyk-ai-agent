"""
MySQL MCP Server (只读查询模式)
基于 fastmcp 框架的 MySQL 数据库查询服务器，仅提供查询功能
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import pymysql
from pymysql.cursors import DictCursor
from fastmcp import FastMCP

# 配置日志输出到 stderr，避免干扰 JSON-RPC 通信
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

# 加载环境变量
load_dotenv()

# 创建 MCP 实例
mcp = FastMCP("MySQL MCP Server (Query Only)")


class MySQLConnection:
    """MySQL 数据库连接管理"""
    
    def __init__(self):
        self.connection = None
    
    def connect(self):
        """建立数据库连接"""
        if self.connection is None:
            self.connection = pymysql.connect(
                host=os.getenv('MYSQL_HOST', 'localhost'),
                port=int(os.getenv('MYSQL_PORT', 3306)),
                user=os.getenv('MYSQL_USER', 'root'),
                password=os.getenv('MYSQL_PASSWORD', ''),
                database=os.getenv('MYSQL_DATABASE'),
                charset=os.getenv('MYSQL_CHARSET', 'utf8mb4'),
                cursorclass=DictCursor
            )
        return self.connection
    
    def disconnect(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None


# 全局连接实例
db = MySQLConnection()


@mcp.tool()
def execute_query(sql: str) -> List[Dict[str, Any]]:
    """
    执行 SELECT 查询语句并返回结果
    
    参数:
        sql: SQL 查询语句（仅支持 SELECT 语句）
    
    返回:
        查询结果列表，每行是一个字典
    
    异常:
        如果查询失败会抛出异常
    """
    conn = db.connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
            return result
    except Exception as e:
        raise Exception(f"查询执行失败: {str(e)}")


@mcp.tool()
def list_databases() -> List[Dict[str, Any]]:
    """
    列出所有数据库
    
    返回:
        数据库列表，每个数据库包含名称等信息
    """
    sql = "SHOW DATABASES"
    conn = db.connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
            # 将结果转换为更友好的格式
            return [{"database": row.get('Database', row.get('database', ''))} for row in result]
    except Exception as e:
        raise Exception(f"获取数据库列表失败: {str(e)}")


@mcp.tool()
def list_tables(database: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    列出指定数据库的所有表
    
    参数:
        database: 数据库名称，如果为 None 则使用当前连接的数据库
    
    返回:
        表列表，每个表包含表名、类型和注释
    """
    if database:
        sql = f"SELECT TABLE_NAME, TABLE_TYPE, TABLE_COMMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA = '{database}'"
    else:
        current_db = os.getenv('MYSQL_DATABASE')
        if not current_db:
            raise Exception("未指定数据库且环境变量 MYSQL_DATABASE 未设置")
        sql = f"SELECT TABLE_NAME, TABLE_TYPE, TABLE_COMMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA = '{current_db}'"
    
    conn = db.connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
            return [
                {
                    "table_name": row.get('TABLE_NAME', row.get('table_name', '')),
                    "table_type": row.get('TABLE_TYPE', row.get('table_type', '')),
                    "table_comment": row.get('TABLE_COMMENT', row.get('table_comment', ''))
                }
                for row in result
            ]
    except Exception as e:
        raise Exception(f"获取表列表失败: {str(e)}")


@mcp.tool()
def describe_table(table_name: str, database: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    获取表结构信息
    
    参数:
        table_name: 表名
        database: 数据库名称，如果为 None 则使用当前连接的数据库
    
    返回:
        表结构信息，包含字段名、类型、是否可空、键、默认值等
    """
    if database:
        sql = f"DESCRIBE `{database}`.`{table_name}`"
    else:
        current_db = os.getenv('MYSQL_DATABASE')
        if not current_db:
            raise Exception("未指定数据库且环境变量 MYSQL_DATABASE 未设置")
        sql = f"DESCRIBE `{current_db}`.`{table_name}`"
    
    conn = db.connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
            return result
    except Exception as e:
        raise Exception(f"获取表结构失败: {str(e)}")


@mcp.tool()
def show_table_status(database: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    显示表的详细信息（引擎、行数、大小等）
    
    参数:
        database: 数据库名称，如果为 None 则使用当前连接的数据库
    
    返回:
        表状态信息列表
    """
    if database:
        sql = f"SHOW TABLE STATUS FROM `{database}`"
    else:
        current_db = os.getenv('MYSQL_DATABASE')
        if not current_db:
            raise Exception("未指定数据库且环境变量 MYSQL_DATABASE 未设置")
        sql = f"SHOW TABLE STATUS FROM `{current_db}`"
    
    conn = db.connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
            return result
    except Exception as e:
        raise Exception(f"获取表状态失败: {str(e)}")


@mcp.tool()
def get_table_indexes(table_name: str, database: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    获取表的索引信息
    
    参数:
        table_name: 表名
        database: 数据库名称，如果为 None 则使用当前连接的数据库
    
    返回:
        索引信息列表
    """
    if database:
        sql = f"SHOW INDEX FROM `{database}`.`{table_name}`"
    else:
        current_db = os.getenv('MYSQL_DATABASE')
        if not current_db:
            raise Exception("未指定数据库且环境变量 MYSQL_DATABASE 未设置")
        sql = f"SHOW INDEX FROM `{current_db}`.`{table_name}`"
    
    conn = db.connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
            return result
    except Exception as e:
        raise Exception(f"获取索引信息失败: {str(e)}")


@mcp.resource("mysql://databases")
def get_databases() -> str:
    """
    获取数据库列表资源
    """
    databases = list_databases()
    return "数据库列表:\n" + "\n".join([f"- {db['database']}" for db in databases])


@mcp.resource("mysql://tables")
def get_tables() -> str:
    """
    获取当前数据库的表列表资源
    """
    tables = list_tables()
    if not tables:
        return "当前数据库中没有表"
    return "表列表:\n" + "\n".join([f"- {table['table_name']} ({table['table_comment']})" for table in tables])


if __name__ == "__main__":
    # 启动 MCP 服务器
    mcp.run()

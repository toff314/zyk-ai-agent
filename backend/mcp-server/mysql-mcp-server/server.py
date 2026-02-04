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
    
    def connect(self, use_database=None):
        """建立数据库连接
        
        参数:
            use_database: 指定要连接的数据库，如果为None则不指定默认数据库
        """
        if self.connection is None:
            # 构建连接参数
            connect_kwargs = {
                'host': os.getenv('MYSQL_HOST', 'localhost'),
                'port': int(os.getenv('MYSQL_PORT', 3306)),
                'user': os.getenv('MYSQL_USER', 'root'),
                'password': os.getenv('MYSQL_PASSWORD', ''),
                'charset': os.getenv('MYSQL_CHARSET', 'utf8mb4'),
                'cursorclass': DictCursor
            }
            
            # 只有在显式指定时才设置database参数
            if use_database:
                connect_kwargs['database'] = use_database
            else:
                # 否则使用环境变量中的值（可能是空字符串）
                db_from_env = os.getenv('MYSQL_DATABASE')
                if db_from_env:
                    connect_kwargs['database'] = db_from_env
            
            self.connection = pymysql.connect(**connect_kwargs)
        return self.connection
    
    def ensure_database(self, database_name):
        """确保当前连接使用指定的数据库"""
        if database_name and (not self.connection or self.connection.db != database_name):
            # 如果连接不在指定数据库，关闭重新连接
            if self.connection:
                self.connection.close()
                self.connection = None
            return self.connect(use_database=database_name)
        return self.connect()
    
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
            # 如果SQL中没有指定数据库名且连接了数据库，先使用该数据库
            current_db = os.getenv('MYSQL_DATABASE')
            if current_db and not any(keyword in sql.upper() for keyword in ['FROM `', 'FROM ', 'UPDATE ', 'INSERT INTO ', 'DELETE FROM ']):
                # 简单的表名查询，添加数据库名前缀
                cursor.execute(f"USE `{current_db}`")
            
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
    # 使用不指定database的连接
    if db.connection:
        db.connection.close()
        db.connection = None
    
    conn = db.connect(use_database=None)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW DATABASES")
            result = cursor.fetchall()
            # 将结果转换为更友好的格式，并过滤系统数据库
            all_dbs = [{"database": row.get('Database', row.get('database', ''))} for row in result]
            # 过滤掉系统数据库
            system_dbs = ['information_schema', 'performance_schema', 'mysql', 'sys']
            user_dbs = [db for db in all_dbs if db['database'] not in system_dbs]
            try:
                cursor.execute(
                    "SELECT TABLE_SCHEMA, MAX(COALESCE(UPDATE_TIME, CREATE_TIME)) AS last_time "
                    "FROM information_schema.TABLES GROUP BY TABLE_SCHEMA"
                )
                time_rows = cursor.fetchall()
                time_map = {
                    row.get("TABLE_SCHEMA", row.get("table_schema")): row.get("last_time")
                    for row in time_rows
                }
            except Exception:
                time_map = {}
            user_dbs.sort(key=lambda item: time_map.get(item["database"]) or "", reverse=True)
            return user_dbs
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
        sql = (
            "SELECT TABLE_NAME, TABLE_TYPE, TABLE_COMMENT, CREATE_TIME, UPDATE_TIME "
            f"FROM information_schema.TABLES WHERE TABLE_SCHEMA = '{database}' "
            "ORDER BY COALESCE(UPDATE_TIME, CREATE_TIME) DESC"
        )
    else:
        current_db = os.getenv('MYSQL_DATABASE')
        if not current_db:
            raise Exception("未指定数据库且环境变量 MYSQL_DATABASE 未设置")
        sql = (
            "SELECT TABLE_NAME, TABLE_TYPE, TABLE_COMMENT, CREATE_TIME, UPDATE_TIME "
            f"FROM information_schema.TABLES WHERE TABLE_SCHEMA = '{current_db}' "
            "ORDER BY COALESCE(UPDATE_TIME, CREATE_TIME) DESC"
        )
    
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
            result.sort(
                key=lambda item: item.get("Update_time")
                or item.get("Create_time")
                or item.get("update_time")
                or item.get("create_time")
                or "",
                reverse=True,
            )
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

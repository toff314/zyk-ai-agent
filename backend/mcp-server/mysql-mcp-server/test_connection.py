#!/usr/bin/env python3
"""
MySQL MCP Server 连接测试脚本
"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    import pymysql
    from pymysql.cursors import DictCursor
    
    print("=" * 50)
    print("MySQL MCP Server 连接测试")
    print("=" * 50)
    
    # 打印连接配置（隐藏密码）
    print("\n数据库配置:")
    print(f"  Host: {os.getenv('MYSQL_HOST')}")
    print(f"  Port: {os.getenv('MYSQL_PORT')}")
    print(f"  User: {os.getenv('MYSQL_USER')}")
    print(f"  Database: {os.getenv('MYSQL_DATABASE')}")
    print(f"  Password: {'*' * len(os.getenv('MYSQL_PASSWORD', ''))}")
    
    # 尝试连接数据库
    print("\n正在连接数据库...")
    conn = pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        database=os.getenv('MYSQL_DATABASE'),
        charset=os.getenv('MYSQL_CHARSET', 'utf8mb4'),
        cursorclass=DictCursor
    )
    print("✓ 数据库连接成功!")
    
    # 列出数据库表
    print("\n正在获取数据库表列表...")
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print(f"✓ 找到 {len(tables)} 个表:")
    for table in tables:
        table_name = list(table.values())[0]
        print(f"  - {table_name}")
    
    # 测试查询
    print("\n执行测试查询...")
    cursor.execute("SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = %s", (os.getenv('MYSQL_DATABASE'),))
    result = cursor.fetchone()
    print(f"✓ 查询成功，数据库中有 {result['count']} 个表")
    
    # 关闭连接
    cursor.close()
    conn.close()
    print("\n✓ 数据库连接已关闭")
    
    print("\n" + "=" * 50)
    print("测试完成! MySQL MCP Server 数据库连接正常")
    print("=" * 50)
    
except ImportError as e:
    print(f"✗ 依赖缺失: {e}")
    print("请运行: pip install pymysql python-dotenv")
    sys.exit(1)
except Exception as e:
    print(f"✗ 连接失败: {e}")
    print("\n请检查:")
    print("1. MySQL 数据库是否正在运行")
    print("2. .env 文件配置是否正确")
    print("3. 网络连接是否正常")
    import traceback
    traceback.print_exc()
    sys.exit(1)

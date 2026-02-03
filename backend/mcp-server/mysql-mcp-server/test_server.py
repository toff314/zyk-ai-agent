"""
MySQL MCP Server 测试脚本
用于测试查询工具的功能
"""

import os
import sys
from dotenv import load_dotenv
import pymysql

# 设置控制台输出编码为 UTF-8，解决 Windows GBK 编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 加载环境变量
load_dotenv()

def test_connection():
    """测试数据库连接"""
    print("=" * 50)
    print("测试数据库连接...")
    print("=" * 50)
    
    try:
        conn = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database=os.getenv('MYSQL_DATABASE'),
            charset=os.getenv('MYSQL_CHARSET', 'utf8mb4')
        )
        print("[OK] 数据库连接成功")
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] 数据库连接失败: {str(e)}")
        return False

def test_query_operations():
    """测试查询操作"""
    print("\n" + "=" * 50)
    print("测试查询操作...")
    print("=" * 50)
    
    try:
        conn = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database=os.getenv('MYSQL_DATABASE'),
            charset=os.getenv('MYSQL_CHARSET', 'utf8mb4')
        )
        cursor = conn.cursor()
        
        # 1. 列出数据库
        print("\n1. 列出所有数据库:")
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()
        for db in databases:
            print(f"   - {db[0]}")
        
        # 2. 列出当前数据库的表
        print("\n2. 列出当前数据库的表:")
        current_db = os.getenv('MYSQL_DATABASE')
        cursor.execute(f"SELECT TABLE_NAME, TABLE_COMMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA = '{current_db}'")
        tables = cursor.fetchall()
        if not tables:
            print("   [INFO] 当前数据库中没有表")
        else:
            for table in tables:
                print(f"   - {table[0]} ({table[1]})")
        
        # 3. 查看表结构（如果有表）
        if tables:
            first_table = tables[0][0]
            print(f"\n3. 查看表 `{first_table}` 的结构:")
            cursor.execute(f"DESCRIBE `{current_db}`.`{first_table}`")
            columns = cursor.fetchall()
            for col in columns:
                print(f"   - {col[0]}: {col[1]} {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
            
            # 4. 查看表状态
            print(f"\n4. 查看表 `{first_table}` 的状态:")
            cursor.execute(f"SHOW TABLE STATUS FROM `{current_db}` LIKE '{first_table}'")
            status = cursor.fetchone()
            print(f"   - 引擎: {status[1]}")
            print(f"   - 行数: {status[4]}")
            print(f"   - 大小: {status[6]} 字节")
            
            # 5. 查看索引
            print(f"\n5. 查看表 `{first_table}` 的索引:")
            cursor.execute(f"SHOW INDEX FROM `{current_db}`.`{first_table}`")
            indexes = cursor.fetchall()
            for idx in indexes:
                print(f"   - {idx[2]} on {idx[4]}")
            
            # 6. 查询表数据（限制 10 条）
            print(f"\n6. 查询表 `{first_table}` 的数据（前 10 条）:")
            cursor.execute(f"SELECT * FROM `{current_db}`.`{first_table}` LIMIT 10")
            rows = cursor.fetchall()
            if not rows:
                print("   [INFO] 表中没有数据")
            else:
                for row in rows:
                    print(f"   {row}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {str(e)}")
        return False

def main():
    """主测试函数"""
    print("\n" + "=" * 50)
    print("MySQL MCP Server 查询功能测试")
    print("=" * 50)
    
    # 检查环境变量
    print("\n检查环境变量:")
    print(f"  MYSQL_HOST: {os.getenv('MYSQL_HOST', '未设置')}")
    print(f"  MYSQL_PORT: {os.getenv('MYSQL_PORT', '未设置')}")
    print(f"  MYSQL_USER: {os.getenv('MYSQL_USER', '未设置')}")
    print(f"  MYSQL_DATABASE: {os.getenv('MYSQL_DATABASE', '未设置')}")
    print(f"  MYSQL_PASSWORD: {'***已设置***' if os.getenv('MYSQL_PASSWORD') else '未设置'}")
    
    # 测试连接
    if not test_connection():
        print("\n[WARNING] 数据库连接失败，请检查配置后重试")
        return
    
    # 测试查询操作
    if test_query_operations():
        print("\n" + "=" * 50)
        print("所有测试通过！")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("测试失败，请检查错误信息")
        print("=" * 50)
    
    print("\n提示: 配置完成后，可以使用 'python server.py' 启动 MCP 服务器")

if __name__ == "__main__":
    main()

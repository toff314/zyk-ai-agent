#!/usr/bin/env python3
"""
测试 MCP MySQL Client 功能
"""
import asyncio
import sys
import os

# 添加 backend 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.mcp_mysql import MCPMySQLClient


async def test_connection():
    """测试数据库基础查询"""
    print("=" * 60)
    print("MCP MySQL Client 功能测试")
    print("=" * 60)
    
    client = MCPMySQLClient()
    
    try:
        # 测试 1: 简单查询
        print("\n[测试 1] 测试简单查询...")
        result = await client.execute_query("SELECT 1 as test, 'success' as message")
        print(f"✓ 简单查询成功: {result}")
        
        # 测试 2: 列出表
        print("\n[测试 2] 测试列出表...")
        tables = await client.execute_query("SHOW TABLES")
        print(f"✓ 找到 {len(tables)} 个表")
        for i, table in enumerate(tables[:5], 1):
            table_name = list(table.values())[0]
            if table_name:
                print(f"  {i}. {table_name}")
        if len(tables) > 5:
            print(f"  ...等 {len(tables)} 个表")
        
        # 测试 3: 查询订单信息
        print("\n[测试 3] 测试查询订单信息...")
        orders = await client.execute_query(
            "SELECT COUNT(*) as total FROM order_info LIMIT 1"
        )
        print(f"✓ 订单总数: {orders[0]['total'] if orders else 0}")
        
        # 测试 4: 获取机构统计（可能需要调整字段名）
        print("\n[测试 4] 测试获取机构统计...")
        try:
            stats = await client.get_hospital_stats()
            print(f"✓ 机构统计查询成功，返回 {len(stats)} 条记录")
            if stats:
                print(f" 示例: {stats[0]}")
        except Exception as e:
            print(f"⚠ 机构统计查询失败: {e}")
            print("  (字段名可能需要根据实际表结构调整)")
        
        # 测试 5: 获取员工信息
        print("\n[测试 5] 测试获取员工信息...")
        try:
            employees = await client.execute_query(
                "SELECT employee_name, COUNT(*) as count FROM order_info GROUP BY employee_name LIMIT 5"
            )
            print(f"✓ 员工统计查询成功，返回 {len(employees)} 条记录")
            for emp in employees:
                print(f"  {emp}")
        except Exception as e:
            print(f"⚠ 员工统计查询失败: {e}")
        
        print("\n" + "=" * 60)
        print("✓ 所有测试完成!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_query_directly():
    """直接测试特定查询"""
    print("\n" + "=" * 60)
    print("直接数据库查询测试")
    print("=" * 60)
    
    client = MCPMySQLClient()
    
    # 测试订单表结构
    print("\n查询 order_info 表结构:")
    structure = await client.execute_query("DESCRIBE order_info")
    print("字段列表:")
    for field in structure[:10]:
        print(f"  - {field.get('Field', field.get('field'))}: {field.get('Type', field.get('type'))}")
    
    # 查看数据量
    print("\n查询订单数量:")
    count_result = await client.execute_query("SELECT COUNT(*) as count FROM order_info")
    print(f"  总订单数: {count_result[0]['count']}")
    
    # 查看最近的订单
    print("\n最近的 3 条订单:")
    recent = await client.execute_query("SELECT * FROM order_info ORDER BY create_time DESC LIMIT 3")
    for i, order in enumerate(recent, 1):
        print(f"  {i}. 订单ID: {order.get('order_id', order.get('id', 'N/A'))}, "
              f"机构: {order.get('institution_name', 'N/A')}, "
              f"金额: {order.get('total_price', order.get('total_amount', 'N/A'))}")


if __name__ == "__main__":
    print("\n开始测试 MCP MySQL Client...\n")
    
    # 运行基础测试
    success = asyncio.run(test_connection())
    
    # 如果基础测试成功，运行更详细的查询测试
    if success:
        asyncio.run(test_query_directly())
    
    print("\n测试结束!")

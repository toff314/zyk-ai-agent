"""
MCP MySQL服务单元测试
"""
import pytest
import subprocess
from unittest.mock import patch, MagicMock
from app.services.mcp_mysql import MCPMySQLClient


@pytest.fixture
def mcp_client():
    """创建MCP MySQL客户端实例"""
    return MCPMySQLClient()


class TestMCPMySQLClient:
    """MCP MySQL客户端测试类"""
    
    @patch('subprocess.Popen')
    def test_execute_query_success(self, mock_popen, mcp_client):
        """测试成功执行查询"""
        # 模拟subprocess.Popen返回值
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            '{"result": [{"id": 1, "name": "test"}]}',
            ""
        )
        
        mock_popen.return_value = mock_process
        
        # 同步方式测试
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                mcp_client.execute_query("SELECT * FROM test_table")
            )
            
            # 验证结果
            assert result == [{"id": 1, "name": "test"}]
            mock_process.stdin.write.assert_called_once()
        finally:
            loop.close()
    
    @patch('subprocess.Popen')
    def test_execute_query_error(self, mock_popen, mcp_client):
        """测试查询失败"""
        # 模拟subprocess.Popen返回值（错误情况）
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (
            "",
            "SQL syntax error"
        )
        
        mock_popen.return_value = mock_process
        
        # 同步方式测试
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            with pytest.raises(Exception) as exc_info:
                loop.run_until_complete(
                    mcp_client.execute_query("INVALID SQL")
                )
            
            assert "MCP Server Error" in str(exc_info.value)
        finally:
            loop.close()
    
    @patch('subprocess.Popen')
    def test_execute_query_timeout(self, mock_popen, mcp_client):
        """测试查询超时"""
        # 模拟超时情况
        mock_process = MagicMock()
        mock_process.communicate.side_effect = subprocess.TimeoutExpired("test", 60)
        mock_process.kill = MagicMock()
        
        mock_popen.return_value = mock_process
        
        # 同步方式测试
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            with pytest.raises(Exception) as exc_info:
                loop.run_until_complete(
                    mcp_client.execute_query("SELECT * FROM test_table")
                )
            
            assert "Query timeout" in str(exc_info.value)
            mock_process.kill.assert_called_once()
        finally:
            loop.close()
    
    @patch('subprocess.Popen')
    def test_execute_query_json_error(self, mock_popen, mcp_client):
        """测试JSON解析错误"""
        # 模拟无效的JSON响应
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("invalid json", "")
        
        mock_popen.return_value = mock_process
        
        # 同步方式测试
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            with pytest.raises(Exception) as exc_info:
                loop.run_until_complete(
                    mcp_client.execute_query("SELECT * FROM test_table")
                )
            
            assert "Failed to parse response" in str(exc_info.value)
        finally:
            loop.close()
    
    @patch('subprocess.Popen')
    def test_execute_query_query_error(self, mock_popen, mcp_client):
        """测试SQL查询错误"""
        # 模拟MCP返回查询错误
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            '{"error": "Table does not exist"}',
            ""
        )
        
        mock_popen.return_value = mock_process
        
        # 同步方式测试
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            with pytest.raises(Exception) as exc_info:
                loop.run_until_complete(
                    mcp_client.execute_query("SELECT * FROM nonexistent_table")
                )
            
            assert "Query Error" in str(exc_info.value)
        finally:
            loop.close()
    
    def test_client_initialization(self, mcp_client):
        """测试客户端初始化"""
        # 验证初始化
        assert mcp_client.server_path == "/home/yuanwu/mysql-mcp-server/server.py"
        assert "MYSQL_HOST" in mcp_client.env
        assert "MYSQL_PORT" in mcp_client.env
        assert "MYSQL_USER" in mcp_client.env
        assert "MYSQL_PASSWORD" in mcp_client.env
        assert "MYSQL_DATABASE" in mcp_client.env


class TestMCPMySQLClientWithMockExecute:
    """使用mock execute_query的测试类"""
    
    @patch.object(MCPMySQLClient, 'execute_query')
    def test_get_hospital_stats(self, mock_execute, mcp_client):
        """测试获取医院统计"""
        # 模拟查询结果
        mock_execute.return_value = [
            {
                "hospital_name": "测试医院",
                "total_orders": 100,
                "total_amount": 10000.0,
                "patient_count": 50
            }
        ]
        
        # 同步方式调用
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(mcp_client.get_hospital_stats())
            
            # 验证调用了execute_query
            mock_execute.assert_called_once()
            assert len(result) == 1
            assert result[0]["hospital_name"] == "测试医院"
        finally:
            loop.close()
    
    @patch.object(MCPMySQLClient, 'execute_query')
    def test_get_medicine_stats(self, mock_execute, mcp_client):
        """测试获取药品统计"""
        # 模拟查询结果
        mock_execute.return_value = [
            {
                "medicine_name": "测试药品",
                "total_quantity": 50,
                "total_cost": 500.0,
                "order_count": 10
            }
        ]
        
        # 同步方式调用
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(mcp_client.get_medicine_stats())
            
            # 验证调用了execute_query
            mock_execute.assert_called_once()
            assert len(result) == 1
            assert result[0]["medicine_name"] == "测试药品"
        finally:
            loop.close()
    
    @patch.object(MCPMySQLClient, 'execute_query')
    def test_get_order_trends(self, mock_execute, mcp_client):
        """测试获取订单趋势"""
        # 模拟查询结果
        mock_execute.return_value = [
            {
                "date": "2026-01-01",
                "order_count": 20,
                "total_amount": 2000.0
            }
        ]
        
        # 同步方式调用
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(mcp_client.get_order_trends(days=7))
            
            # 验证调用了execute_query
            mock_execute.assert_called_once()
            assert len(result) == 1
            assert result[0]["date"] == "2026-01-01"
        finally:
            loop.close()
    
    @patch.object(MCPMySQLClient, 'execute_query')
    def test_get_employee_stats(self, mock_execute, mcp_client):
        """测试获取员工统计"""
        # 模拟查询结果
        mock_execute.return_value = [
            {
                "employee_name": "测试员工",
                "processed_orders": 30,
                "total_amount": 3000.0
            }
        ]
        
        # 同步方式调用
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(mcp_client.get_employee_stats())
            
            # 验证调用了execute_query
            mock_execute.assert_called_once()
            assert len(result) == 1
            assert result[0]["employee_name"] == "测试员工"
        finally:
            loop.close()

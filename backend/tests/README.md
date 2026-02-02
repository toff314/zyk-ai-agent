# MCP MySQL服务单元测试

## 测试文件
- `test_mcp_mysql.py` - MCP MySQL客户端单元测试

## 测试覆盖范围

### TestMCPMySQLClient 类

1. **test_execute_query_success** - 测试成功执行查询
   - 模拟subprocess.Popen成功返回
   - 验证返回正确的查询结果

2. **test_execute_query_error** - 测试查询失败（MCP错误）
   - 模拟subprocess返回错误码
   - 验证抛出正确的异常信息

3. **test_execute_query_timeout** - 测试查询超时
   - 模拟subprocess.TimeoutExpired
   - 验证进程被正确终止

4. **test_execute_query_json_error** - 测试JSON解析错误
   - 模拟无效的JSON响应
   - 验证抛出解析异常

5. **test_execute_query_query_error** - 测试SQL查询错误
   - 模拟MCP返回查询错误
   - 验证抛出查询错误异常

6. **test_get_hospital_stats** - 测试获取医院统计
   - Mock execute_query方法
   - 验证调用和返回结果

7. **test_get_medicine_stats** - 测试获取药品统计
   - Mock execute_query方法
   - 验证调用和返回结果

8. **test_get_order_trends** - 测试获取订单趋势
   - Mock execute_query方法
   - 验证调用和返回结果

9. **test_get_employee_stats** - 测试获取员工统计
   - Mock execute_query方法
   - 验证调用和返回结果

10. **test_client_initialization** - 测试客户端初始化
    - 验证server_path和env变量正确设置

## 运行测试

### 方法1: 使用pytest（推荐）

```bash
cd backend
source venv/bin/activate
pip install pytest pytest-asyncio pytest-coverage
pytest tests/test_mcp_mysql.py -v
```

### 方法2: 使用unittest

```bash
cd backend
source venv/bin/activate
python -m unittest tests.test_mcp_mysql -v
```

### 方法3: 直接运行（在代码末尾）

```bash
cd backend
source venv/bin/activate
python tests/test_mcp_mysql.py
```

## 如果pip安装失败

### 使用国内镜像源

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pytest pytest-asyncio pytest-coverage
```

### 或使用阿里云镜像

```bash
pip install -i https://mirrors.aliyun.com/pypi/simple/ pytest pytest-asyncio
```

## 生成测试覆盖率报告

```bash
pytest tests/test_mcp_mysql.py --cov=app.services.mcp_mysql --cov-report=html
```

覆盖率报告将生成在 `htmlcov/` 目录下。

## 修复说明

### Python路径问题修复

**问题**: 代码中硬编码使用 `python` 命令，但系统中可能没有该命令。

**解决方案**: 使用 `sys.executable` 获取当前Python解释器路径：

```python
# 修改前
process = subprocess.Popen(
    ["python", self.server_path],
    ...
)

# 修改后  
process = subprocess.Popen(
    [sys.executable, self.server_path],
    ...
)
```

这确保使用正确的Python解释器路径（如 `/home/yuanwu/zyk-db-agent/backend/venv/bin/python`）。

## 测试策略

测试使用了Mock技术，不需要真实的：
- MySQL数据库连接
- MCP Server服务器实例
- 外部依赖

所有测试都是隔离的，可以快速运行，不依赖外部服务。

## 依赖项

测试需要以下包：
- `pytest>=7.4.0` - 测试框架
- `pytest-asyncio>=0.21.0` - 异步测试支持

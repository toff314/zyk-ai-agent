# MySQL MCP Server

基于 Python 3.14 和 fastmcp 框架的 MySQL 数据库交互服务器，为 AI 助手提供与 MySQL 数据库交互的能力。

## 功能特性

### 数据库操作工具
- **execute_query**: 执行 SELECT 查询语句
- **execute_update**: 执行 INSERT/UPDATE/DELETE 等 DML 语句
- **list_databases**: 列出所有数据库
- **list_tables**: 列出指定数据库的所有表

### 表结构管理
- **describe_table**: 获取表结构信息
- **show_table_status**: 显示表的详细信息（引擎、行数、大小等）
- **get_table_indexes**: 获取表的索引信息

### DDL 操作
- **create_table**: 创建表
- **drop_table**: 删除表
- **truncate_table**: 清空表数据

### 事务管理
- **begin_transaction**: 开始事务
- **commit_transaction**: 提交事务
- **rollback_transaction**: 回滚事务

### 资源访问
- **mysql://databases**: 获取数据库列表资源
- **mysql://tables**: 获取当前数据库的表列表资源

## 安装

### 1. 克隆项目

```bash
cd mysql-mcp-server
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并配置数据库连接信息：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# MySQL 数据库连接配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database

# 连接池配置
MYSQL_CHARSET=utf8mb4
MYSQL_AUTOCOMMIT=true
```

## 使用方法

### 启动服务器

```bash
python server.py
```

### MCP 客户端配置

在支持 MCP 的客户端（如 Claude Desktop）中配置此服务器。

#### Claude Desktop 配置示例

编辑 Claude Desktop 配置文件（通常在 `~/Library/Application Support/Claude/claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "mysql": {
      "command": "python",
      "args": ["/path/to/mysql-mcp-server/server.py"],
      "env": {
        "MYSQL_HOST": "localhost",
        "MYSQL_PORT": "3306",
        "MYSQL_USER": "root",
        "MYSQL_PASSWORD": "your_password",
        "MYSQL_DATABASE": "your_database"
      }
    }
  }
}
```

## 工具使用示例

### 查询数据

```python
# 在 Claude 中询问：
# 执行查询：SELECT * FROM users WHERE age > 25

# 结果会返回查询结果列表
```

### 列出所有数据库

```python
# 在 Claude 中询问：
# 列出所有数据库

# 结果会返回数据库列表
```

### 获取表结构

```python
# 在 Claude 中询问：
# 查看表 users 的结构

# 结果会返回字段信息、类型、是否可空等
```

### 创建表

```python
# 在 Claude 中询问：
# 创建一个名为 products 的表，包含 id、name、price 字段

# 结果会生成并执行 CREATE TABLE 语句
```

### 事务操作

```python
# 在 Claude 中询问：
# 开始一个事务，插入两条记录，然后提交

# 示例流程：
# 1. begin_transaction()
# 2. execute_update("INSERT INTO users (name, age) VALUES ('Alice', 30)")
# 3. execute_update("INSERT INTO users (name, age) VALUES ('Bob', 25)")
# 4. commit_transaction()
```

## 技术栈

- **Python 3.14**: 编程语言
- **fastmcp**: MCP 服务器框架
- **pymysql**: MySQL 数据库驱动
- **python-dotenv**: 环境变量管理

## 安全注意事项

1. **密码安全**: 不要将 `.env` 文件提交到版本控制系统
2. **SQL 注入**: 此服务器直接执行 SQL 语句，请确保在 AI 助手中使用时注意输入验证
3. **权限控制**: 建议使用具有适当权限的数据库账号，避免使用 root 账号
4. **连接加密**: 生产环境建议使用 SSL/TLS 加密数据库连接

## 项目结构

```
mysql-mcp-server/
├── server.py           # MCP 服务器主文件
├── requirements.txt    # Python 依赖
├── .env.example       # 环境变量示例
├── .env               # 环境变量配置（不提交）
└── README.md          # 项目文档
```

## 开发

### 添加新工具

在 `server.py` 中使用 `@mcp.tool()` 装饰器添加新工具：

```python
@mcp.tool()
def your_tool_name(param: str) -> Dict[str, Any]:
    """
    工具描述
    """
    # 实现逻辑
    return result
```

### 添加新资源

在 `server.py` 中使用 `@mcp.resource()` 装饰器添加新资源：

```python
@mcp.resource("mysql://your-resource")
def your_resource() -> str:
    """
    资源描述
    """
    # 实现逻辑
    return "资源内容"
```

## 故障排除

### 连接失败

- 检查 MySQL 服务是否正在运行
- 确认 `.env` 文件中的连接配置是否正确
- 验证数据库用户权限

### 依赖安装失败

- 确保使用 Python 3.14
- 尝试升级 pip: `pip install --upgrade pip`
- 使用虚拟环境：`python -m venv venv && source venv/bin/activate`

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

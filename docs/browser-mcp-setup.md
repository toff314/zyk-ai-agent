# Browser MCP Server 安装与配置

本项目的普通对话 Agent 支持浏览网页（工具名：`browse_web`），使用 Playwright Python 库直接实现浏览器自动化功能。

## 1. 前置要求

- Python 虚拟环境
- 后端服务所在机器能访问目标网页

## 2. 安装方式

### 2.1 安装 Playwright

在项目根目录执行：

```bash
cd backend
source venv/bin/activate
pip install playwright==1.40.0
```

如果虚拟环境不存在，先创建：

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2.2 安装浏览器驱动

```bash
playwright install chromium
```

## 3. 后端配置

在 `backend/.env` 中配置：

```env
# 浏览器调用超时（秒）
BROWSER_MCP_TIMEOUT=60
```

旧的 `BROWSER_MCP_COMMAND` 配置已不再需要。

## 4. 启动后端

```bash
cd backend
source venv/bin/activate
python main.py
```

## 5. 验证

在前端聊天中输入：

```
https://example.com 这个网页说了什么？
```

或使用搜索关键词：

```
Python 编程教程
```

后端会调用 `browse_web` 工具并返回网页快照内容。

## 6. 实现说明

本项目已改用 **Playwright Python 库**直接实现浏览器功能，不再依赖外部 MCP Server。

### 优势

- **无需 Node.js 环境**：纯 Python 实现，降低依赖复杂度
- **更好的控制**：直接管理浏览器实例和请求
- **更容易调试**：标准 Python 异常处理

### 核心代码

核心实现在 `backend/app/services/mcp_browser.py`：

```python
class MCPBrowserClient:
    """使用 Playwright 直接实现的浏览器客户端"""
    
    async def browse(self, query_or_url: str) -> str:
        # 1. 判断是URL还是搜索关键词
        # 2. 使用 Playwright 导航到页面
        # 3. 获取页面文本内容并返回
```

## 7. 常见问题

### 7.1 ModuleNotFoundError: No module named 'playwright'

确保已激活虚拟环境并安装了依赖：

```bash
cd backend
source venv/bin/activate
pip install playwright
playwright install chromium
```

### 7.2 Playwright 找不到浏览器驱动

运行安装命令：

```bash
playwright install chromium
```

### 7.3 浏览页面超时

在 `backend/.env` 中增加超时时间：

```env
BROWSER_MCP_TIMEOUT=120
```

### 7.4 无法访问外网

请确保服务器网络配置正确，或使用代理环境变量：

```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
```

### 7.5 页面内容为空

某些现代网站使用 JavaScript 动态渲染，可能需要调整等待策略。当前实现使用 `networkidle` 等待网络请求完成。

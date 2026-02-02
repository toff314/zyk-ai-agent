# 数据运营AI平台

基于Vue3、FastAPI、LangChain和MCP的数据分析AI平台。

## 项目结构

```
zyk-db-agent/
├── backend/          # Python后端
│   ├── app/
│   │   ├── api/     # API路由
│   │   ├── agents/  # LangChain Agent
│   │   ├── models/  # 数据库模型
│   │   ├── services/ # 业务服务层
│   │   └── ...
│   ├── main.py      # 启动入口
│   └── requirements.txt
├── frontend/        # Vue3前端
│   ├── src/
│   │   ├── api/     # API调用
│   │   ├── components/ #组件
│   │   ├── views/   # 页面视图
│   │   └── ...
│   └── package.json
└── .clinerules/     # 任务文档
```

## 核心功能

### 1. 用户管理
- 用户登录/退出（JWT认证）
- 管理员用户管理（添加/删除/重置密码）
- 权限控制（admin vs 普通用户）

### 2. 对话功能
- 数据分析Agent：分析中药代煎平台数据（医院订单、药品消耗、员工工作等）
- 研发质量分析Agent：GitLab代码审查、提交统计
- 普通对话：大模型通用对话

### 3. 交互特性
- @符号：快捷选择研发人名（代码审查）或数据库（数据分析）
- #符号：快捷输入提示词模板
- 流式响应：实时显示AI回复
- 对话历史记录

### 4. 配置管理
- 模型API配置（API Key、URL、Model ID）
- MySQL配置（MCP服务器）
- GitLab配置

## 快速开始

### 后端启动

```bash
cd backend

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（可选）
cp .env.example .env

# 启动服务
python main.py
```

后端服务将在 http://localhost:8000 启动

API文档：http://localhost:8000/docs

默认管理员账号：
- 用户名：admin
- 密码：admin123!

### 前端启动

```bash
cd frontend

# 安装依赖
npm install --registry=https://registry.npmmirror.com


# 启动开发服务器
npm run dev
```

前端服务将在 http://localhost:5173 启动

## 技术栈

### 后端
- **框架**：FastAPI 0.104.1
- **Agent框架**：LangChain 0.1.0
- **数据库**：SQLite (SQLAlchemy 2.0.23)
- **认证**：JWT (PyJWT 2.8.0)
- **GitLab集成**：python-gitlab 4.3.0
- **MCP集成**：自定义MCP客户端

### 前端
- **框架**：Vue 3.4.21 (Composition API + TypeScript)
- **UI组件**：Element Plus 2.6.0
- **状态管理**：Pinia 2.1.7
- **路由**：Vue Router 4.3.0
- **HTTP客户端**：Axios 1.6.7
- **Markdown渲染**：markdown-it 14.1.0
- **代码高亮**：highlight.js 11.9.0

## Agent使用说明

### 数据分析Agent

**能力**：
- 分析医院订单情况
- 统计药品消耗
- 评估员工工作效率
- 生成医院排名、地区患者排名
- 分析订单趋势变化

**使用方法**：
1. 切换到"数据分析"模式
2. 使用@符号选择数据库或表
3. 输入自然语言问题，如："分析最近一周的订单趋势"

### 代码审查Agent

**能力**：
- 查看研发人员的提交记录
- 对指定提交进行代码审查
- 生成详细的代码质量报告

**使用方法**：
1. 切换到"研发质量分析"模式
2. 使用@符号选择研发人名查看提交
3. 使用@提交ID进行代码审查

### 普通对话Agent

**能力**：
- 通用问答
- 信息查询
- 辅助对话

## 配置说明

### MCP MySQL Server配置

在数据库配置中设置MySQL连接信息：

```json
{
  "host": "数据库主机",
  "port": 3306,
  "user": "用户名",
  "password": "密码",
  "database": "数据库名"
}
```

### GitLab配置

```json
{
  "url": "GitLab地址",
  "token": "访问令牌"
}
```

### 模型配置

```json
{
  "api_key": "API密钥",
  "base_url": "API地址",
  "model": "模型名称"
}
```

## 数据库表结构

- **users**: 用户表
- **conversations**: 对话表
- **messages**: 消息表
- **gitlab_users**: GitLab用户缓存表
- **config**: 配置表

## 开发说明

### 后端API

- 认证：`/api/v1/auth/*`
- 用户管理：`/api/v1/users/*`
- 对话：`/api/v1/chat/*`
- 配置：`/api/v1/config/*`

### 前端路由

- `/login`: 登录页
- `/`: 主页面（聊天界面）
- `/users`: 用户管理（仅管理员）
- `/settings`: 配置管理（仅管理员）

## 注意事项

1. 首次启动会自动创建管理员账号（admin/admin123!）
2. 生产环境请修改默认密码
3. 配置JWT密钥以确保安全性
4. MCP Server需要在独立进程中运行
5. 前端需要配置正确的后端API地址

## License

MIT

"""
Agent服务层 - 实现LangChain Agent
"""
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from typing import Optional, Dict, Any
import logging
from .mcp_mysql import mcp_mysql_client
from .mcp_browser import mcp_browser_client
from .gitlab import gitlab_service
from app.agents.prompts import CHAT_PROMPT, DATA_ANALYSIS_PROMPT
from app.utils.code_review_prompt import render_code_review_prompt
from app.utils.gitlab_commit_lookup import resolve_commit_project_id
from app.utils.gitlab_username import normalize_gitlab_username

logger = logging.getLogger(__name__)


class AgentService:
    """Agent服务基类"""
    
    def __init__(self, model_config: Dict[str, Any]):
        """
        初始化Agent服务
        
        参数:
            model_config: 模型配置，包括 api_key, base_url, model 等
        """
        self.llm = ChatOpenAI(
            api_key=model_config.get("api_key"),
            base_url=model_config.get("base_url"),
            model=model_config.get("model", "gpt-3.5-turbo"),
            temperature=0.7,
            streaming=True
        )
        self.agent_graph = None
    
    async def initialize(self, system_prompt: str, tools: list):
        """
        初始化Agent
        
        参数:
            system_prompt: 系统提示词
            tools: 工具列表
        """
        try:
            # 使用新的 create_agent API
            self.agent_graph = create_agent(
                model=self.llm,
                tools=tools,
                system_prompt=system_prompt,
                debug=True
            )
            
            logger.info("Agent初始化成功")
            
        except Exception as e:
            logger.error(f"Agent初始化失败: {str(e)}")
            raise
    
    async def query(self, message: str) -> str:
        """
        查询Agent
        
        参数:
            message: 用户消息
        
        返回:
            str: Agent响应
        """
        if not self.agent_graph:
            raise RuntimeError("Agent未初始化")
        
        try:
            # 使用新的 API 调用 agent
            inputs = {"messages": [{"role": "user", "content": message}]}
            result = await self.agent_graph.ainvoke(inputs)
            
            # 提取最终回复
            messages = result.get("messages", [])
            if messages:
                # 获取最后一个 AI 消息
                for msg in reversed(messages):
                    if hasattr(msg, 'content') and msg.content:
                        return str(msg.content)
            
            return "未获得响应"
            
        except Exception as e:
            logger.error(f"Agent查询失败: {str(e)}")
            return f"查询失败: {str(e)}"


class DataAnalysisAgent(AgentService):
    """数据分析Agent"""
    
    async def initialize(self, model_config: Dict[str, Any]):
        """
        初始化数据分析Agent
        
        参数:
            model_config: 模型配置
        """
        self.llm = ChatOpenAI(
            api_key=model_config.get("api_key"),
            base_url=model_config.get("base_url"),
            model=model_config.get("model", "gpt-3.5-turbo"),
            temperature=0.7
        )
        
        async def _load_mysql_config():
            from app.models.database import get_db
            from app.models.config import Config
            from sqlalchemy import select
            import json

            db_gen = get_db()
            db = await db_gen.__anext__()
            try:
                result = await db.execute(select(Config).where(Config.key == "mysql_config"))
                config = result.scalar_one_or_none()
                if not config:
                    return None, "错误：未配置MySQL连接信息"
                mysql_config = json.loads(config.value)
                if not mysql_config.get("enabled"):
                    return None, "错误：MySQL未启用"
                return mysql_config, None
            finally:
                try:
                    await db_gen.aclose()
                except Exception:
                    pass

        # 创建MySQL查询工具
        async def execute_mysql_query(query: str) -> str:
            """执行MySQL查询"""
            try:
                mysql_config, error_message = await _load_mysql_config()
                if error_message:
                    return error_message

                results = await mcp_mysql_client.execute_query(query, mysql_config=mysql_config)
                return self._format_results(results)
            except Exception as e:
                import traceback
                logger.error(f"执行MySQL查询失败: {str(e)}\n{traceback.format_exc()}")
                return f"查询失败: {str(e)}"

        async def list_databases() -> list | str:
            """列出数据库"""
            try:
                mysql_config, error_message = await _load_mysql_config()
                if error_message:
                    return error_message
                return await mcp_mysql_client.list_databases(mysql_config=mysql_config)
            except Exception as e:
                return f"获取数据库列表失败: {str(e)}"

        async def list_tables(database: str | None = None) -> list | str:
            """列出表"""
            try:
                mysql_config, error_message = await _load_mysql_config()
                if error_message:
                    return error_message
                return await mcp_mysql_client.list_tables(database, mysql_config=mysql_config)
            except Exception as e:
                return f"获取表列表失败: {str(e)}"

        async def describe_table(table_name: str, database: str | None = None) -> list | str:
            """查看表结构"""
            try:
                mysql_config, error_message = await _load_mysql_config()
                if error_message:
                    return error_message
                return await mcp_mysql_client.describe_table(table_name, database, mysql_config=mysql_config)
            except Exception as e:
                return f"获取表结构失败: {str(e)}"

        async def show_table_status(database: str | None = None) -> list | str:
            """查看表状态"""
            try:
                mysql_config, error_message = await _load_mysql_config()
                if error_message:
                    return error_message
                return await mcp_mysql_client.show_table_status(database, mysql_config=mysql_config)
            except Exception as e:
                return f"获取表状态失败: {str(e)}"

        async def get_table_indexes(table_name: str, database: str | None = None) -> list | str:
            """查看索引"""
            try:
                mysql_config, error_message = await _load_mysql_config()
                if error_message:
                    return error_message
                return await mcp_mysql_client.get_table_indexes(table_name, database, mysql_config=mysql_config)
            except Exception as e:
                return f"获取索引信息失败: {str(e)}"
        
        await super().initialize(
            DATA_ANALYSIS_PROMPT,
            [
                execute_mysql_query,
                list_databases,
                list_tables,
                describe_table,
                show_table_status,
                get_table_indexes,
            ],
        )
    
    def _format_results(self, results: list) -> str:
        """格式化查询结果"""
        if not results:
            return "查询结果为空"
        
        # 创建Markdown表格
        headers = list(results[0].keys())
        table = "| " + " | ".join(headers) + " |\n"
        table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        
        for row in results:
            table += "| " + " | ".join(str(row[h]) for h in headers) + " |\n"
        
        return f"查询结果：\n\n{table}\n\n共 {len(results)} 条记录"


class CodeReviewAgent(AgentService):
    """代码审查Agent"""
    
    async def initialize(self, model_config: Dict[str, Any], system_prompt: Optional[str] = None):
        """
        初始化代码审查Agent
        
        参数:
            model_config: 模型配置
        """
        self.llm = ChatOpenAI(
            api_key=model_config.get("api_key"),
            base_url=model_config.get("base_url"),
            model=model_config.get("model", "gpt-3.5-turbo"),
            temperature=0.3  # 更低的温度以提高一致性
        )
        
        # 创建获取用户提交的工具
        async def get_user_commits(username: str) -> str:
            """获取用户提交记录"""
            try:
                normalized = normalize_gitlab_username(username)
                if not normalized:
                    return "没有找到提交记录"
                commits = await gitlab_service.get_user_commits(normalized, limit=5)
                return self._format_commits(commits)
            except Exception as e:
                return f"获取提交失败: {str(e)}"
        
        # 创建查看代码差异的工具
        async def get_commit_diff(commit_id: str, project_id: int | None = None) -> str:
            """查看提交的代码差异"""
            try:
                resolved_project_id = project_id
                if resolved_project_id is None:
                    from app.models.database import get_db

                    db_gen = get_db()
                    db = await db_gen.__anext__()
                    try:
                        resolved_project_id = await resolve_commit_project_id(db, commit_id)
                    finally:
                        try:
                            await db_gen.aclose()
                        except Exception:
                            pass

                if resolved_project_id is None:
                    return "获取代码差异失败: 未提供project_id，且未在本地记录中找到该commit。"

                diff = await gitlab_service.get_commit_diff(commit_id, resolved_project_id)
                return diff
            except Exception as e:
                return f"获取代码差异失败: {str(e)}"

        async def list_projects() -> list:
            """列出项目"""
            try:
                if not gitlab_service:
                    return []
                return await gitlab_service.list_projects()
            except Exception as e:
                return [f"获取项目失败: {str(e)}"]

        async def list_users() -> list:
            """列出用户"""
            try:
                if not gitlab_service:
                    return []
                return await gitlab_service.list_users()
            except Exception as e:
                return [f"获取用户失败: {str(e)}"]

        async def list_branches(project_id: int) -> list:
            """列出分支"""
            try:
                if not gitlab_service:
                    return []
                return await gitlab_service.list_branches(project_id)
            except Exception as e:
                return [f"获取分支失败: {str(e)}"]

        async def list_commits(project_id: int, limit: int = 20, ref_name: str | None = None) -> list:
            """列出提交"""
            try:
                if not gitlab_service:
                    return []
                return await gitlab_service.list_commits(project_id, limit=limit, ref_name=ref_name)
            except Exception as e:
                return [f"获取提交失败: {str(e)}"]

        final_prompt = system_prompt or render_code_review_prompt("", "")

        await super().initialize(
            final_prompt,
            [
                get_user_commits,
                get_commit_diff,
                list_projects,
                list_users,
                list_branches,
                list_commits,
            ],
        )
    
    def _format_commits(self, commits: list) -> str:
        """格式化提交记录"""
        if not commits:
            return "没有找到提交记录"
        
        result = "最近提交记录：\n\n"
        
        for i, commit in enumerate(commits, 1):
            result += f"{i}. {commit['title']}\n"
            result += f"   - 提交ID: {commit['id']}\n"
            result += f"   - 项目: {commit['project_name']}\n"
            result += f"   - 时间: {commit['authored_date']}\n\n"
        
        return result


class ChatAgent(AgentService):
    """普通对话Agent"""
    
    async def initialize(self, model_config: Dict[str, Any]):
        """
        初始化普通对话Agent
        
        参数:
            model_config: 模型配置
        """
        self.llm = ChatOpenAI(
            api_key=model_config.get("api_key"),
            base_url=model_config.get("base_url"),
            model=model_config.get("model", "gpt-3.5-turbo"),
            temperature=0.7
        )

        async def browse_web(query_or_url: str) -> str:
            """浏览网页或搜索关键词"""
            try:
                # 在线程池中运行同步的 Playwright 调用，避免阻塞事件循环
                import asyncio
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(None, mcp_browser_client.browse, query_or_url)
            except Exception as e:
                return f"浏览失败: {str(e)}"

        await super().initialize(CHAT_PROMPT, [browse_web])


# Agent工厂
class AgentFactory:
    """Agent工厂类"""
    
    @staticmethod
    async def create_agent(
        mode: str,
        model_config: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> AgentService:
        """
        创建Agent实例
        
        参数:
            mode: Agent模式 (data_analysis, code_review, normal)
            model_config: 模型配置
        
        返回:
            AgentService: Agent实例
        """
        if mode == "data_analysis":
            agent = DataAnalysisAgent(model_config)
        elif mode == "code_review":
            agent = CodeReviewAgent(model_config)
        elif mode == "normal":
            agent = ChatAgent(model_config)
        else:
            raise ValueError(f"不支持的Agent模式: {mode}")
        
        if mode == "code_review":
            await agent.initialize(model_config, system_prompt=system_prompt)
        else:
            await agent.initialize(model_config)
        return agent

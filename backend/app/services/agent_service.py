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
from app.agents.prompts import CHAT_PROMPT

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
        
        # 创建MySQL查询工具
        async def execute_mysql_query(query: str) -> str:
            """执行MySQL查询"""
            try:
                from sqlalchemy.ext.asyncio import AsyncSession
                from app.models.database import get_db
                from app.models.config import Config
                from sqlalchemy import select
                import json
                
                # 异步获取数据库会话和MySQL配置
                db_gen = get_db()
                db = await db_gen.__anext__()
                
                try:
                    # 获取MySQL配置
                    result = await db.execute(select(Config).where(Config.key == "mysql_config"))
                    config = result.scalar_one_or_none()
                    if not config:
                        return "错误：未配置MySQL连接信息"
                    
                    mysql_config = json.loads(config.value)
                    if not mysql_config.get("enabled"):
                        return "错误：MySQL未启用"
                    
                    # 使用MCP MySQL客户端执行查询，传递配置参数
                    results = await mcp_mysql_client.execute_query(query, mysql_config=mysql_config)
                    return self._format_results(results)
                finally:
                    try:
                        await db_gen.aclose()
                    except:
                        pass
            except Exception as e:
                import traceback
                logger.error(f"执行MySQL查询失败: {str(e)}\n{traceback.format_exc()}")
                return f"查询失败: {str(e)}"
        
        # 系统提示词
        system_prompt = """
        你是一个专业的数据分析师，专注于中药代煎平台的数据分析。

        ## 你的能力
        - 分析社区医院订单情况
        - 统计各类药品消耗
        - 评估代煎中心员工工作效率
        - 生成医院排名、地区患者排名
        - 分析订单趋势变化

        ## 可用工具
        - execute_mysql_query：用于查询数据库中的业务数据

        ## 回答要求
        1. 首先使用execute_mysql_query工具获取数据
        2. 基于查询结果提供准确的数据分析
        3. 使用表格和图表展示数据（Markdown格式）
        4. 提供可操作的业务建议
        5. 语言简洁专业，易于理解

        ## 主要表结构（参考）
        - orders（订单表）：包含医院、药品、时间等信息
        - medicines（药品表）：药品信息
        - hospitals（医院表）：医院信息
        - employees（员工表）：员工信息
        """
        
        await super().initialize(system_prompt, [execute_mysql_query])
    
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
    
    async def initialize(self, model_config: Dict[str, Any]):
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
                commits = await gitlab_service.get_user_commits(username, limit=5)
                return self._format_commits(commits)
            except Exception as e:
                return f"获取提交失败: {str(e)}"
        
        # 创建查看代码差异的工具
        async def get_commit_diff(commit_id: str) -> str:
            """查看提交的代码差异"""
            try:
                diff = await gitlab_service.get_commit_diff(commit_id)
                return diff
            except Exception as e:
                return f"获取代码差异失败: {str(e)}"
        
        # 系统提示词
        system_prompt = """
        你是一个资深的代码审查专家，精通多种编程语言和最佳实践。

        ## 审查维度
        1. **代码质量**：可读性、可维护性、规范性
        2. **功能正确性**：逻辑是否正确，边界条件处理
        3. **性能优化**：是否有性能问题，优化建议
        4. **安全性**：是否存在安全漏洞
        5. **测试覆盖**：测试用例是否充分

        ## 审查格式
        对于每个问题，请按以下格式：
        - **严重程度**: 高/中/低
        - **问题描述**: 具体描述问题
        - **代码位置**: 文件名和行号（如果有）
        - **建议修改**: 提供改进建议

        ## 回答要求
        1. 先给出总体评价（优秀/良好/一般/需改进）
        2. 按严重程度排序列出问题
        3. 对于优秀代码给予表扬
        4. 提供具体的修改建议和示例代码
        5. 语气友好，鼓励改进

        ## 使用工具
        - 当用户询问某人的提交时，使用"get_user_commits"工具
        - 当用户提到提交ID时，使用"get_commit_diff"工具获取代码
        """
        
        await super().initialize(system_prompt, [get_user_commits, get_commit_diff])
    
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
    async def create_agent(mode: str, model_config: Dict[str, Any]) -> AgentService:
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
        
        await agent.initialize(model_config)
        return agent

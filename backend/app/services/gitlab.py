"""
GitLab API服务（通过 MCP GitLab 工具）
"""
from typing import List
from datetime import datetime
from app.config.settings import settings
from app.models.gitlab_user import GitLabUser
from app.models.database import safe_commit
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.mcp_gitlab import MCPGitLabClient


class GitLabService:
    """GitLab服务"""
    
    def __init__(self):
        """初始化GitLab客户端"""
        if not settings.GITLAB_TOKEN:
            raise ValueError("GITLAB_TOKEN未配置")

        self.client = MCPGitLabClient()
    
    async def get_all_users(self, db: AsyncSession) -> List[dict]:
        """
        获取所有GitLab用户并更新统计信息
        
        参数:
            db: 数据库会话
        
        返回:
            List[dict]: 用户列表
        """
        try:
            users = await self.client.list_users(None)
            user_list = []
            
            for user in users:
                commits_week = 0
                commits_month = 0

                # 更新或创建数据库记录
                result = await db.execute(
                    select(GitLabUser).where(GitLabUser.id == user.get("id"))
                )
                db_user = result.scalar_one_or_none()
                
                user_data = {
                    "id": user.get("id"),
                    "username": user.get("username"),
                    "name": user.get("name"),
                    "avatar_url": user.get("avatar_url"),
                    "commits_week": commits_week,
                    "commits_month": commits_month
                }
                
                if db_user:
                    # 更新现有记录
                    db_user.commits_week = commits_week
                    db_user.commits_month = commits_month
                    db_user.updated_at = datetime.utcnow()
                else:
                    # 创建新记录
                    db_user = GitLabUser(
                        id=user.get("id"),
                        username=user.get("username") or "",
                        name=user.get("name"),
                        avatar_url=user.get("avatar_url"),
                        commits_week=commits_week,
                        commits_month=commits_month
                    )
                    db.add(db_user)
                
                user_list.append(user_data)
            
            await safe_commit(db)
            return user_list
            
        except Exception as e:
            raise Exception(f"获取GitLab用户失败: {e}")

    async def list_projects(self) -> List[dict]:
        """获取GitLab项目列表（通过 MCP）"""
        try:
            return await self.client.list_projects(None)
        except Exception as e:
            raise Exception(f"获取GitLab项目列表失败: {e}")

    async def list_users(self) -> List[dict]:
        """获取GitLab用户列表（通过 MCP）"""
        try:
            return await self.client.list_users(None)
        except Exception as e:
            raise Exception(f"获取GitLab用户列表失败: {e}")

    async def list_branches(self, project_id: int) -> List[dict]:
        """获取GitLab分支列表（通过 MCP）"""
        try:
            return await self.client.list_branches(None, project_id)
        except Exception as e:
            raise Exception(f"获取GitLab分支列表失败: {e}")

    async def list_commits(
        self,
        project_id: int,
        limit: int = 20,
        ref_name: str | None = None,
    ) -> List[dict]:
        """获取GitLab提交列表（通过 MCP）"""
        try:
            return await self.client.list_commits(None, project_id, limit=limit, ref_name=ref_name)
        except Exception as e:
            raise Exception(f"获取GitLab提交列表失败: {e}")
    
    async def get_user_commits(self, username: str, limit: int = 10) -> List[dict]:
        """
        获取指定用户的最近提交
        
        参数:
            username: 用户名
            limit: 返回数量
        
        返回:
            List[dict]: 提交列表
        """
        try:
            return await self.client.get_user_commits(None, username, limit=limit)
            
        except Exception as e:
            raise Exception(f"获取用户提交失败: {e}")
    
    async def get_commit_diff(self, commit_id: str, project_id: int) -> dict:
        """
        获取指定提交的代码差异
        
        参数:
            commit_id: 提交ID
            project_id: 项目ID
        
        返回:
            dict: 提交详情和差异
        """
        try:
            commit = await self.client.get_commit_diff(None, project_id, commit_id)
            if isinstance(commit, dict):
                commit.setdefault("project_id", project_id)
                if "diff" not in commit and "diffs" in commit:
                    commit["diff"] = commit.get("diffs")
            return commit
            
        except Exception as e:
            raise Exception(f"获取提交差异失败: {e}")


# 创建全局服务实例
gitlab_service = GitLabService() if settings.GITLAB_TOKEN else None

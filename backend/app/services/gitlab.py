"""
GitLab API服务
"""
import gitlab
from typing import List, Optional
from datetime import datetime, timedelta
from app.config.settings import settings
from app.models.gitlab_user import GitLabUser
from app.models.database import safe_commit
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update


class GitLabService:
    """GitLab服务"""
    
    def __init__(self):
        """初始化GitLab客户端"""
        if not settings.GITLAB_TOKEN:
            raise ValueError("GITLAB_TOKEN未配置")
        
        self.gl = gitlab.Gitlab(settings.GITLAB_URL, private_token=settings.GITLAB_TOKEN)
    
    async def get_all_users(self, db: AsyncSession) -> List[dict]:
        """
        获取所有GitLab用户并更新统计信息
        
        参数:
            db: 数据库会话
        
        返回:
            List[dict]: 用户列表
        """
        try:
            # 获取所有用户
            users = self.gl.users.list(all=True)
            
            user_list = []
            one_week_ago = datetime.now() - timedelta(days=7)
            one_month_ago = datetime.now() - timedelta(days=30)
            
            for user in users:
                # 统计本周提交
                commits_week = self._count_commits(user.id, since=one_week_ago)
                
                # 统计本月提交
                commits_month = self._count_commits(user.id, since=one_month_ago)
                
                # 更新或创建数据库记录
                result = await db.execute(
                    select(GitLabUser).where(GitLabUser.id == user.id)
                )
                db_user = result.scalar_one_or_none()
                
                user_data = {
                    "id": user.id,
                    "username": user.username,
                    "name": user.name,
                    "avatar_url": user.avatar_url,
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
                        id=user.id,
                        username=user.username,
                        name=user.name,
                        avatar_url=user.avatar_url,
                        commits_week=commits_week,
                        commits_month=commits_month
                    )
                    db.add(db_user)
                
                user_list.append(user_data)
            
            await safe_commit(db)
            return user_list
            
        except Exception as e:
            raise Exception(f"获取GitLab用户失败: {e}")
    
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
            # 获取用户
            user = self.gl.users.list(username=username)[0]
            
            # 获取用户的所有项目
            projects = user.projects.list(membership=True, all=True)
            
            commits = []
            for project in projects:
                try:
                    # 获取项目的提交
                    project_commits = project.commits.list(all=True)
                    
                    # 过滤该用户的提交
                    user_commits = [
                        commit for commit in project_commits
                        if commit.author_name == user.name or commit.author_email == user.email
                    ]
                    
                    for commit in user_commits[:limit]:
                        commits.append({
                            "id": commit.id,
                            "title": commit.title,
                            "message": commit.message,
                            "author_name": commit.author_name,
                            "authored_date": commit.authored_date,
                            "project_id": project.id,
                            "project_name": project.name,
                            "web_url": commit.web_url
                        })
                        
                except Exception:
                    continue
            
            # 按时间排序
            commits.sort(key=lambda x: x["authored_date"], reverse=True)
            
            return commits[:limit]
            
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
            # 获取项目
            project = self.gl.projects.get(project_id)
            
            # 获取提交
            commit = project.commits.get(commit_id)
            
            # 获取差异
            diff = commit.diff()
            
            return {
                "id": commit.id,
                "title": commit.title,
                "message": commit.message,
                "author_name": commit.author_name,
                "authored_date": commit.authored_date,
                "project_id": project_id,
                "project_name": project.name,
                "diff": diff
            }
            
        except Exception as e:
            raise Exception(f"获取提交差异失败: {e}")
    
    def _count_commits(self, user_id: int, since: datetime) -> int:
        """
        统计用户在指定时间后的提交数
        
        参数:
            user_id: 用户ID
            since: 起始时间
        
        返回:
            int: 提交数量
        """
        try:
            total = 0
            user = self.gl.users.get(user_id)
            projects = user.projects.list(membership=True, all=True)
            
            for project in projects:
                try:
                    commits = project.commits.list(since=since, all=True)
                    user_commits = [
                        commit for commit in commits
                        if commit.author_name == user.name or commit.author_email == user.email
                    ]
                    total += len(user_commits)
                except Exception:
                    continue
            
            return total
        except Exception:
            return 0


# 创建全局服务实例
gitlab_service = GitLabService() if settings.GITLAB_TOKEN else None

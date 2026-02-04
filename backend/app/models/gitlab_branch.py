"""GitLab branch cache model."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index
from app.models.database import Base


class GitLabBranch(Base):
    __tablename__ = "gitlab_branches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, index=True)
    name = Column(String(200), index=True)
    commit_sha = Column(String(64))
    committed_date = Column(String(50))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_gitlab_branch_project_name", "project_id", "name", unique=True),
    )

    def __repr__(self) -> str:
        return f"<GitLabBranch(project_id={self.project_id}, name='{self.name}')>"

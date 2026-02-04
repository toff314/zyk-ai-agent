"""GitLab commit cache model."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index
from app.models.database import Base


class GitLabCommit(Base):
    __tablename__ = "gitlab_commits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, index=True)
    branch = Column(String(200), index=True)
    commit_sha = Column(String(64), index=True)
    title = Column(String(500))
    author_name = Column(String(200))
    created_at = Column(String(50))
    web_url = Column(String(500))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index(
            "idx_gitlab_commit_project_branch_sha",
            "project_id",
            "branch",
            "commit_sha",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<GitLabCommit(project_id={self.project_id}, sha='{self.commit_sha}')>"

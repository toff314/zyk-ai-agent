"""GitLab commit diff cache model."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index
from app.models.database import Base


class GitLabCommitDiff(Base):
    __tablename__ = "gitlab_commit_diffs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, index=True)
    commit_sha = Column(String(64), index=True)
    old_path = Column(String(500))
    new_path = Column(String(500))
    diff = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index(
            "idx_gitlab_diff_project_commit_path",
            "project_id",
            "commit_sha",
            "new_path",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<GitLabCommitDiff(project_id={self.project_id}, commit='{self.commit_sha}')>"

"""GitLab project cache model."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.models.database import Base


class GitLabProject(Base):
    __tablename__ = "gitlab_projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    path_with_namespace = Column(String(300), unique=True, index=True)
    web_url = Column(String(500))
    last_activity_at = Column(String(50))
    remark = Column(String(255), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<GitLabProject(id={self.id}, path='{self.path_with_namespace}')>"

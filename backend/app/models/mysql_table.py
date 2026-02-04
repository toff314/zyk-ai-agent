"""
MySQL表元数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index, Boolean
from app.models.database import Base


class MySQLTable(Base):
    """MySQL表信息"""
    __tablename__ = "mysql_tables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    database_name = Column(String(255), nullable=False, index=True)
    table_name = Column(String(255), nullable=False, index=True)
    table_type = Column(String(50), nullable=True)
    table_comment = Column(String(500), nullable=True)
    remark = Column(String(255), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_mysql_tables_db_table", "database_name", "table_name", unique=True),
    )

    def __repr__(self):
        return f"<MySQLTable(database='{self.database_name}', table='{self.table_name}')>"

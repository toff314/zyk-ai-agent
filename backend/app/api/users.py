"""
用户管理API路由（仅管理员）
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from app.models.database import get_db, safe_commit
from app.models.user import User
from app.middleware.auth import get_current_admin, get_current_user
from app.utils.security import get_password_hash


router = APIRouter(prefix="/api/v1/users", tags=["用户管理"])


class CreateUserRequest(BaseModel):
    """创建用户请求"""
    username: str
    password: str
    role: str = "user"  # 默认为普通用户


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    role: str
    created_at: str


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    new_password: str


@router.get("", response_model=list[UserResponse])
async def list_users(
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    获取所有用户列表（仅管理员）
    
    参数:
        current_admin: 当前管理员用户
        db: 数据库会话
    
    返回:
        list[UserResponse]: 用户列表
    """
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    
    return [
        {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "created_at": user.created_at.isoformat()
        }
        for user in users
    ]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: CreateUserRequest,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    创建新用户（仅管理员）
    
    参数:
        user_data: 用户数据
        current_admin: 当前管理员用户
        db: 数据库会话
    
    返回:
        UserResponse: 创建的用户信息
    """
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == user_data.username))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 验证角色
    if user_data.role not in ["admin", "user"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="角色必须是 admin 或 user"
        )
    
    # 创建用户
    new_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role
    )
    
    db.add(new_user)
    await safe_commit(db)
    await db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "username": new_user.username,
        "role": new_user.role,
        "created_at": new_user.created_at.isoformat()
    }


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    删除用户（仅管理员）
    
    参数:
        user_id: 用户ID
        current_admin: 当前管理员用户
        db: 数据库会话
    
    返回:
        dict: 删除结果
    """
    # 不能删除自己
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己"
        )
    
    # 检查用户是否存在
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 删除用户（会级联删除相关对话和消息）
    await db.execute(delete(User).where(User.id == user_id))
    await safe_commit(db)
    
    return {"message": "用户删除成功"}


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    password_data: ResetPasswordRequest,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    重置用户密码（仅管理员）
    
    参数:
        user_id: 用户ID
        password_data: 新密码数据
        current_admin: 当前管理员用户
        db: 数据库会话
    
    返回:
        dict: 重置结果
    """
    # 检查用户是否存在
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 更新密码
    user.password_hash = get_password_hash(password_data.new_password)
    await safe_commit(db)
    
    return {"message": "密码重置成功"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户信息
    
    参数:
        current_user: 当前登录用户
    
    返回:
        UserResponse: 用户信息
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "created_at": current_user.created_at.isoformat()
    }

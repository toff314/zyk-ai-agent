"""
认证API路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.models.database import get_db
from app.models.user import User
from app.utils.security import verify_password, create_access_token
from app.middleware.auth import get_current_user


router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应"""
    token: str
    user: dict


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录
    
    参数:
        login_data: 登录数据（用户名和密码）
        db: 数据库会话
    
    返回:
        LoginResponse: 包含JWT令牌和用户信息
    """
    # 查询用户
    result = await db.execute(select(User).where(User.username == login_data.username))
    user = result.scalar_one_or_none()
    
    # 验证用户和密码
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 创建访问令牌
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return {
        "token": access_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role
        }
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """
    获取当前用户信息
    
    参数:
        current_user: 当前登录用户
    
    返回:
        dict: 用户信息
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "created_at": current_user.created_at.isoformat()
    }


@router.post("/logout")
async def logout():
    """
    用户登出
    
    注意：由于JWT是无状态的，客户端需要删除存储的令牌
    """
    return {"message": "登出成功"}

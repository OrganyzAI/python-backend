from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt import PyJWTError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import get_engine
from app.core.security import ALGORITHM
from app.models.user import User
from app.enums.user_enum import UserStatus

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """
    Get the current authenticated user from the JWT token.

    Args:
        token: JWT token from the Authorization header

    Returns:
        The authenticated User object

    Raises:
        HTTPException: If the token is invalid or the user is not found/active
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except (PyJWTError, Exception):
        raise credentials_exception

    with Session(get_engine()) as session:
        statement = select(User).where(User.id == user_id)
        user = session.exec(statement).first()

        if user is None:
            raise credentials_exception

        if user.status != UserStatus.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not active",
            )

        return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Get the current active user.

    Args:
        current_user: The current user from get_current_user

    Returns:
        The active User object

    Raises:
        HTTPException: If the user is not active
    """
    if current_user.status != UserStatus.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


CurrentUserDep = Annotated[User, Depends(get_current_active_user)]
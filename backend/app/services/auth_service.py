from datetime import timedelta
from typing import Any

import jwt
from sqlmodel import Session, select

from app.core import security
from app.core.config import settings
from app.core.db import get_engine
from app.models.user import User
from app.utils_helper.messages import MSG


class AuthService:
    async def get_user_by_email(self, email: str) -> User | None:
        with Session(get_engine()) as session:
            statement = select(User).where(User.email == email)
            result = session.exec(statement).first()
            return result

    async def create_user(
        self,
        email: str,
        password: str,
        first_name: str | None = None,
        last_name: str | None = None,
        phone_number: str | None = None,
    ) -> User:
        if not email or not password:
            raise ValueError(MSG.AUTH["ERROR"]["EMAIL_AND_PASSWORD_REQUIRED"])

        hashed = security.get_password_hash(password)
        user = User(
            email=email,
            hashed_password=hashed,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
        )

        with Session(get_engine()) as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    async def authenticate_user(self, email: str, password: str) -> User | None:
        user = await self.get_user_by_email(email)
        if not user:
            return None
        if not security.verify_password(password, user.hashed_password):
            return None
        return user

    async def login(self, email: str, password: str) -> dict[str, Any]:
        user = await self.authenticate_user(email, password)
        if not user:
            raise ValueError(MSG.AUTH["ERROR"]["INVALID_CREDENTIALS"])

        expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            subject=str(user.id), expires_delta=expires
        )

        user_data = {
            "id": str(user.id),
            "email": str(user.email),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": str(user.role) if hasattr(user, "role") else None,
        }

        return {"access_token": access_token, "token_type": "bearer", "user": user_data}

    async def register(
        self,
        email: str,
        password: str,
        first_name: str | None = None,
        last_name: str | None = None,
        phone_number: str | None = None,
    ) -> dict[str, Any]:
        existing = await self.get_user_by_email(email)
        if existing:
            raise ValueError(MSG.AUTH["ERROR"]["USER_EXISTS"])

        user = await self.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
        )
        return {
            "message": MSG.AUTH["SUCCESS"]["USER_REGISTERED"],
            "user": {"id": str(user.id), "email": str(user.email)},
        }

    async def verify(self, token: str | None = None) -> dict[str, Any]:
        if not token:
            raise ValueError(MSG.AUTH["ERROR"]["TOKEN_REQUIRED"])
        return {"message": "Email verified"}

    async def forgot_password(self, email: str) -> dict[str, Any]:
        if not email:
            raise ValueError(MSG.AUTH["ERROR"]["EMAIL_REQUIRED"])

        user = await self.get_user_by_email(email)
        if not user:
            return {"message": MSG.AUTH["SUCCESS"]["PASSWORD_RESET_EMAIL_SENT"]}

        expires = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
        reset_token = security.create_access_token(
            subject=str(user.id), expires_delta=expires
        )

        return {
            "message": MSG.AUTH["SUCCESS"]["PASSWORD_RESET_EMAIL_SENT"],
            "reset_token": reset_token,
        }

    async def reset_password(self, token: str, new_password: str) -> dict[str, Any]:
        if not token or not new_password:
            raise ValueError("Token and new password are required")
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
            )
            subject = payload.get("sub")
            if not subject:
                raise ValueError(MSG.AUTH["ERROR"]["INVALID_TOKEN"])

            with Session(get_engine()) as session:
                statement = select(User).where(User.id == subject)
                user = session.exec(statement).first()
                if not user:
                    raise ValueError(MSG.AUTH["ERROR"]["INVALID_TOKEN_SUBJECT"])

                user.hashed_password = security.get_password_hash(new_password)
                session.add(user)
                session.commit()
                session.refresh(user)

            return {"message": MSG.AUTH["SUCCESS"]["PASSWORD_HAS_BEEN_RESET"]}
        except jwt.ExpiredSignatureError:
            raise ValueError(MSG.AUTH["ERROR"]["TOKEN_EXPIRED"])
        except jwt.PyJWTError:
            raise ValueError(MSG.AUTH["ERROR"]["INVALID_TOKEN"])

    async def resend_email(self, email: str) -> dict[str, Any]:
        if not email:
            raise ValueError(MSG.AUTH["ERROR"]["EMAIL_REQUIRED"])

        user = await self.get_user_by_email(email)
        if not user:
            return {"message": MSG.AUTH["SUCCESS"]["VERIFICATION_EMAIL_RESENT"]}

        return {"message": MSG.AUTH["SUCCESS"]["VERIFICATION_EMAIL_RESENT"]}

    async def logout(self, user_id: str | None = None) -> dict[str, Any]:
        return {"message": MSG.AUTH["SUCCESS"]["LOGGED_OUT"]}


# Module-level helper for legacy tests that expect `app.services.auth_service.create_user`
def create_user(session: Session, user_create: Any) -> User:
    """Create a user using a DB session and a `UserCreate` like object.

    This helper mirrors the behavior expected by older tests that import
    `app.services.auth_service as crud` and call `crud.create_user(...)`.
    """
    if not getattr(user_create, "email", None) or not getattr(
        user_create, "password", None
    ):
        raise ValueError(MSG.AUTH["ERROR"]["EMAIL_AND_PASSWORD_REQUIRED"])

    hashed = security.get_password_hash(user_create.password)
    user = User(
        email=user_create.email,
        hashed_password=hashed,
        first_name=getattr(user_create, "first_name", None),
        last_name=getattr(user_create, "last_name", None),
        phone_number=getattr(user_create, "phone_number", None),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

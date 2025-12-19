from datetime import timedelta
from typing import Any
from uuid import UUID

import jwt
from sqlmodel import Session, select

from app.core import security
from app.core.config import settings
from app.core.db import get_engine
from app.enums.otp_enum import EmailTokenStatus
from app.enums.user_enum import UserStatus
from app.models.otp import OTP
from app.models.user import User
from app.services.webengage_email import send_email as webengage_send_email
from app.utils_helper.messages import MSG


class AuthService:
    async def get_user_by_email(
        self, email: str, session: Session | None = None
    ) -> User | None:
        statement = select(User).where(User.email == email)
        if session is None:
            with Session(get_engine()) as local_session:
                result = local_session.exec(statement).first()
                return result
        result = session.exec(statement).first()
        return result

    async def send_token(self, to: str, verify_url: str, campaign_id: str) -> None:
        await webengage_send_email(
            to_email=to, verify_url=verify_url, campaign_id=campaign_id
        )

    async def create_user(
        self,
        email: str,
        password: str,
        session: Session | None = None,
    ) -> User:
        if not email or not password:
            raise ValueError(MSG.AUTH["ERROR"]["EMAIL_AND_PASSWORD_REQUIRED"])
        hashed = security.get_password_hash(password)
        user = User(
            email=email,
            hashed_password=hashed,
        )
        own_session = None
        try:
            if session is None:
                own_session = Session(get_engine())
                session_ctx = own_session
                session_ctx.add(user)
                session_ctx.commit()
                session_ctx.refresh(user)
            else:
                session.add(user)
                session.flush()
                try:
                    session.refresh(user)
                except Exception:
                    pass
        finally:
            if own_session is not None:
                own_session.close()

        expires = timedelta(
            hours=getattr(
                settings,
                "EMAIL_VERIFY_TOKEN_EXPIRE_HOURS",
                settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            )
        )
        verify_token = security.create_access_token(
            subject=str(user.id), expires_delta=expires
        )
        frontend_base = getattr(settings, "FRONTEND_URL", "")
        verify_url = (
            f"{frontend_base.rstrip('/')}/verify?token={verify_token}"
            if frontend_base
            else verify_token
        )

        await self.send_token(
            to=email,
            verify_url=verify_url,
            campaign_id=settings.WEBENGAGE_CAMPAIGN_REGISTER_ID or "email_verification",
        )

        return user

    async def authenticate_user(
        self, email: str, password: str, session: Session | None = None
    ) -> User | None:
        user = await self.get_user_by_email(email, session=session)
        if not user:
            return None
        if not security.verify_password(password, user.hashed_password):
            return None
        return user

    async def login(self, email: str, password: str) -> dict[str, Any]:
        with Session(get_engine()) as session:
            user = await self.authenticate_user(email, password, session=session)
            if not user:
                raise ValueError(MSG.AUTH["ERROR"]["INVALID_CREDENTIALS"])

            if getattr(user, "status", None) == UserStatus.banned:
                raise ValueError(MSG.AUTH["ERROR"]["CONTACT_ADMIN"])
            if getattr(user, "status", None) == UserStatus.inactive:
                raise ValueError(MSG.AUTH["ERROR"]["EMAIL_NOT_VERIFIED"])

            expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = security.create_access_token(
                subject=str(user.id), expires_delta=expires
            )
            try:
                user.token = access_token
                session.add(user)
                session.commit()
                session.refresh(user)
            except Exception:
                session.rollback()

            user_data = {
                "id": str(user.id),
                "email": str(user.email),
                "role": str(user.role) if hasattr(user, "role") else None,
            }

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": user_data,
            }

    async def register(
        self,
        email: str,
        password: str,
    ) -> dict[str, Any]:
        existing = await self.get_user_by_email(email)
        if existing:
            raise ValueError(MSG.AUTH["ERROR"]["USER_EXISTS"])

        with Session(get_engine()) as session:
            try:
                with session.begin():
                    user = await self.create_user(
                        email=email,
                        password=password,
                        session=session,
                    )

                    expires = timedelta(
                        hours=getattr(
                            settings,
                            "EMAIL_VERIFY_TOKEN_EXPIRE_HOURS",
                            settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
                        )
                    )
                    verify_token = security.create_access_token(
                        subject=str(user.id), expires_delta=expires
                    )

                    frontend_base = getattr(settings, "FRONTEND_URL", "")
                    verify_url = (
                        f"{frontend_base.rstrip('/')}/verify?token={verify_token}"
                        if frontend_base
                        else verify_token
                    )

                    await self.send_token(
                        to=email,
                        verify_url=verify_url,
                        campaign_id=settings.WEBENGAGE_CAMPAIGN_REGISTER_ID
                        or "email_verification",
                    )

                    await self.save_token(user.id, verify_token, session=session)

                return {
                    "message": MSG.AUTH["SUCCESS"]["USER_REGISTERED"],
                    "user": {"id": str(user.id), "email": str(user.email)},
                }
            except Exception:
                raise

    async def verify(self, token: str | None = None) -> dict[str, Any] | None:
        with Session(get_engine()) as session:
            try:
                if not token:
                    raise ValueError(MSG.AUTH["ERROR"]["TOKEN_REQUIRED"])
                payload = jwt.decode(
                    token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
                )
                subject = payload.get("sub")
                if not subject:
                    raise ValueError(MSG.AUTH["ERROR"]["INVALID_TOKEN"])

                otp_record = session.exec(
                    select(OTP).where(
                        OTP.email_token == token,
                        OTP.token_status == EmailTokenStatus.active,
                    )
                ).first()

                if otp_record is None or getattr(otp_record, "user_id", None) is None:
                    raise ValueError(MSG.AUTH["ERROR"]["INVALID_TOKEN_SUBJECT"])

                statement = select(User).where(User.id == otp_record.user_id)
                user = session.exec(statement).first()
                if not user:
                    raise ValueError(MSG.AUTH["ERROR"]["INVALID_TOKEN_SUBJECT"])

                user.status = UserStatus.active
                otp_record.token_status = EmailTokenStatus.used
                session.add(user)
                session.commit()
                session.refresh(user)

                return {
                    "message": MSG.AUTH["SUCCESS"]["EMAIL_VERIFIED"],
                    "user": {"id": str(user.id), "email": str(user.email)},
                }

            except jwt.ExpiredSignatureError:
                raise ValueError(MSG.AUTH["ERROR"]["TOKEN_EXPIRED"])
            except jwt.PyJWTError:
                raise ValueError(MSG.AUTH["ERROR"]["INVALID_TOKEN"])

    async def forgot_password(self, email: str) -> dict[str, Any]:
        try:
            with Session(get_engine()) as session:
                if not email:
                    raise ValueError(MSG.AUTH["ERROR"]["EMAIL_REQUIRED"])

                user = await self.get_user_by_email(email, session=session)
                if not user:
                    return {"message": MSG.AUTH["SUCCESS"]["PASSWORD_RESET_EMAIL_SENT"]}

                expires = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
                reset_token = security.create_access_token(
                    subject=str(user.id), expires_delta=expires
                )
                frontend_base = getattr(settings, "FRONTEND_URL", "")
                reset_url = (
                    f"{frontend_base.rstrip('/')}/reset-password?token={reset_token}"
                    if frontend_base
                    else reset_token
                )
                await self.send_token(
                    to=email,
                    verify_url=reset_url,
                    campaign_id=settings.WEBENGAGE_CAMPAIGN_FORGOT_PASSWORD_ID
                    or "password_reset",
                )
                await self.save_token(user.id, reset_token, session=session)

                session.commit()
                session.refresh(user)
                session.close()

                return {
                    "message": MSG.AUTH["SUCCESS"]["PASSWORD_RESET_EMAIL_SENT"],
                    "reset_token": reset_token,
                }
        except ValueError as e:
            session.rollback()
            session.close()
            raise e

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
                token_record = session.exec(
                    select(OTP).where(
                        OTP.email_token == token,
                        OTP.token_status == EmailTokenStatus.active,
                    )
                ).first()
                if (
                    token_record is None
                    or getattr(token_record, "user_id", None) is None
                ):
                    raise ValueError(MSG.AUTH["ERROR"]["INVALID_TOKEN_SUBJECT"])
                statement = select(User).where(User.id == token_record.user_id)
                user = session.exec(statement).first()
                if not user:
                    raise ValueError(MSG.AUTH["ERROR"]["INVALID_TOKEN_SUBJECT"])

                user.hashed_password = security.get_password_hash(new_password)
                token_record.token_status = EmailTokenStatus.used
                session.add(user)
                session.add(token_record)
                session.commit()
                session.refresh(user)
                session.close()

            return {"message": MSG.AUTH["SUCCESS"]["PASSWORD_HAS_BEEN_RESET"]}
        except jwt.ExpiredSignatureError:
            raise ValueError(MSG.AUTH["ERROR"]["TOKEN_EXPIRED"])
        except jwt.PyJWTError:
            raise ValueError(MSG.AUTH["ERROR"]["INVALID_TOKEN"])

    async def resend_email(self, email: str) -> dict[str, Any]:
        with Session(get_engine()) as session:
            try:
                if not email:
                    raise ValueError(MSG.AUTH["ERROR"]["EMAIL_REQUIRED"])
                user = await self.get_user_by_email(email, session=session)
                if not user:
                    raise ValueError(MSG.AUTH["ERROR"]["USER_NOT_FOUND"])
                if getattr(user, "status", None) == UserStatus.active:
                    raise ValueError(MSG.AUTH["ERROR"]["EMAIL_ALREADY_VERIFIED"])
                expires = timedelta(
                    hours=getattr(
                        settings,
                        "EMAIL_VERIFY_TOKEN_EXPIRE_HOURS",
                        settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
                    )
                )
                verify_token = security.create_access_token(
                    subject=str(user.id), expires_delta=expires
                )

                frontend_base = getattr(settings, "FRONTEND_URL", "")
                verify_url = (
                    f"{frontend_base.rstrip('/')}/verify?token={verify_token}"
                    if frontend_base
                    else verify_token
                )

                await self.send_token(
                    to=email,
                    verify_url=verify_url,
                    campaign_id=settings.WEBENGAGE_CAMPAIGN_REGISTER_ID
                    or "email_verification",
                )
                await self.save_token(user.id, verify_token, session=session)
                session.commit()
                session.refresh(user)
                session.close()
                return {"message": MSG.AUTH["SUCCESS"]["VERIFICATION_EMAIL_RESENT"]}

            except ValueError as e:
                session.rollback()
                raise e

    async def logout(self, user_id: str | None = None) -> dict[str, Any]:
        return {"message": MSG.AUTH["SUCCESS"]["LOGGED_OUT"]}

    async def save_token(
        self, user_id: UUID, token: str, session: Session | None = None
    ) -> None:
        otp = OTP(
            user_id=user_id,
            email_token=token,
            token_status=EmailTokenStatus.active,
        )
        if session is None:
            with Session(get_engine()) as local_session:
                local_session.add(otp)
                local_session.commit()
                local_session.refresh(otp)
        else:
            session.add(otp)
            session.flush()
            try:
                session.refresh(otp)
            except Exception:
                pass
        return


def create_user(session: Session, user_create: Any) -> User:
    if not getattr(user_create, "email", None) or not getattr(
        user_create, "password", None
    ):
        raise ValueError(MSG.AUTH["ERROR"]["EMAIL_AND_PASSWORD_REQUIRED"])

    hashed = security.get_password_hash(user_create.password)
    user = User(
        email=user_create.email,
        hashed_password=hashed,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

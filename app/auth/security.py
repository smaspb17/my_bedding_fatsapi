from datetime import datetime, UTC, timedelta
from typing import Annotated
from redis.asyncio import Redis
from jwt import InvalidTokenError
from pydantic import ValidationError
from redis import asyncio as aioredis
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from passlib.context import CryptContext
from sqlalchemy import select

from app.auth.schemas import TokenData
from app.core.config import settings
from app.db.database import AsyncSessionDep
from app.db.models.users import User

SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token",
    auto_error=False,
    # scopes={
    #     "me": "Доступ к собственным данным",
    #     "product:read": "Чтение данных",
    #     "product:create": "Создание данных",
    #     "product:update": "Обновление данных",
    #     "product:delete": "Удаление данных",
    # },
)

# Клиент для чёрного списка токенов
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
blacklist_tokens_redis = None


async def get_blacklist_tokens_redis():
    global blacklist_tokens_redis
    if blacklist_tokens_redis is None:
        blacklist_tokens_redis = await aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
    return blacklist_tokens_redis


async def is_token_blacklisted(
        token: str,
        redis: Annotated[Redis, Depends(get_blacklist_tokens_redis)]
):
    """Проверка, есть ли токен в чёрном списке"""
    return await redis.exists(f"blacklist:{token}")


def verify_password(plain_password, hashed_password):
    """Сравнение введенного пароля с хешем пароля в БД"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Хеширование пароля"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Создание jwt-токена"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    # непосредственное создание токена
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str):
    """Декодирование jwt-токена"""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload


async def authenticate_user(session: AsyncSessionDep, email: str, password: str):
    """Аутентификация пользователя"""
    user = await get_user(session, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


async def has_permissions(
    security_scopes: SecurityScopes,
    # token: Annotated[str, Depends(oauth2_scheme)],
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
    redis=Depends(get_blacklist_tokens_redis),
):
    print(f"{security_scopes.scopes=}")
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
    token_data = None
    if not token or await is_token_blacklisted(token, redis):
        user_scopes = ["shop:read"]
    else:
        try:
            payload = decode_token(token)
            email = payload.get("sub")
            if email is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Ошибка токена: email is None",
                    headers={"WWW-Authenticate": authenticate_value},
                )
            token_scopes = payload.get("scopes")
            token_data = TokenData(scopes=token_scopes, email=email)
            user_scopes = token_data.scopes
            print(f"{token_data.scopes=}")
        except (InvalidTokenError, ValidationError) as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Ошибка токена: {err}",
                headers={"WWW-Authenticate": authenticate_value},
            )
    for scope in security_scopes.scopes:
        if scope not in user_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав",
                headers={"WWW-Authenticate": authenticate_value},
            )
    return token_data


async def get_user(session: AsyncSessionDep, email: str) -> User:
    """Получение пользователя из БД"""
    query = select(User).where(User.email == email)
    user_db = await session.scalar(query)
    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь с таким email не найден",
        )
    return user_db


async def get_current_user(
    session: AsyncSessionDep,
    token_data: Annotated[TokenData | None, Depends(has_permissions)] = None,
):
    """Получение текущего пользователя по токену"""
    if not token_data:
        return None
    try:
        user = await get_user(session, email=token_data.email)
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь не активирован",
            )
        return user
    except HTTPException:
        return None

"""Basic Auth"""
# from fastapi.security import HTTPBasic, HTTPBasicCredentials

# security = HTTPBasic()
# AuthCredsDep = Annotated[HTTPBasicCredentials, Depends(security)]
# credentials: AuthCredsDep

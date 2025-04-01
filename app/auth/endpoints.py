from datetime import timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status, APIRouter, Security, Form
from fastapi.security import (
    OAuth2PasswordRequestForm,
)
from sqlalchemy import select, exists
from fastapi.responses import JSONResponse

from app.auth.permissions import get_role_scopes
from app.auth.schemas import RegisterUserCreate, RegisterUserPublic, Token
from app.auth.security import (
    get_password_hash,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    oauth2_scheme,
    get_blacklist_tokens_redis,
    authenticate_user,
    get_current_user,
)

from app.db.database import AsyncSessionDep
from app.db.models.users import User


router = APIRouter(
    prefix="/auth",
    tags=["Аутентификация и авторизация"],
    responses={
        # 401: {'detail': 'string'},
        # 403: {'detail': 'string'},
    },
)


@router.post(
    "/token",
    summary="Получение jwt-токена",
    description="Получение jwt-токена",
)
async def login(
    session: AsyncSessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    print(f"{form_data.scopes=}")
    user = await authenticate_user(
        session, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не корректный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Пользователь не активирован")

    # Получаем разрешения для роли пользователя
    role = user.role
    role_scopes = await get_role_scopes(role)
    # Формируем список scopes на основе разрешений роли
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "scopes": role_scopes},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


@router.post(
    "/register",
    response_model=RegisterUserPublic,
    summary="Регистрация пользователя",
    description="Регистрация пользователя",
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    session: AsyncSessionDep,
    form_data: Annotated[RegisterUserCreate, Form()],
    current_user: Annotated[
        User | None, Depends(get_current_user)
    ] = None,  # Опционально токен
) -> RegisterUserPublic:
    if form_data.role != "buyer":
        if current_user is None or current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Необходимы права администратора",
                headers={"WWW-Authenticate": 'Bearer scope="user:create"'},
            )
        # проверка токена и получение юзера из БД
        print(f"{current_user.role.value=}")
    if form_data.password != form_data.repeat_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Пароли не совпадают"
        )
    is_exists = await session.scalar(
        select(exists().where(User.email == form_data.email))
    )
    if is_exists:
        raise HTTPException(
            status_code=400, detail="Пользователь с таким email существует"
        )
    user_db = User(**form_data.model_dump(exclude={"password", "repeat_password"}))
    user_db.hashed_password = get_password_hash(form_data.password)
    session.add(user_db)
    await session.commit()
    return RegisterUserPublic.model_validate(user_db)


@router.get("/users/me")
async def read_users_me(
    current_user: Annotated[User, Security(get_current_user, scopes=["me:read"])],
):
    return RegisterUserPublic.model_validate(current_user)


@router.post("/logout", summary="Аннулирование токена")
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    redis=Depends(get_blacklist_tokens_redis),
):
    """Аннулирование токена: добавление в чёрный список"""
    if not token:
        raise HTTPException(
            status_code=400, detail="Токен отсутствует. Вы не вошли в систему"
        )
    await redis.setex(f"blacklist:{token}", 3600, "blacklisted")  # TTL 60 минут
    return JSONResponse(status_code=200, content={"message": "Токен аннулирован"})

# app/auth/endpoints.py

from datetime import UTC, datetime, timedelta
import logging
from typing import Annotated
from redis.asyncio import Redis
from fastapi import (
    Depends,
    HTTPException,
    status,
    APIRouter,
    Security,
    Form,
)
from fastapi.security import (
    OAuth2PasswordRequestForm,
)
from sqlalchemy import select
from fastapi.responses import JSONResponse

from app.auth.permissions import get_role_scopes
from app.auth.schemas import (
    ChangePassword,
    RegisterUserCreate,
    RegisterUserPublic,
    SetPassword,
    Token,
)
from app.auth.security import (
    get_password_hash,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    oauth2_scheme,
    get_blacklist_tokens_redis_client,
    authenticate_user,
    get_current_user,
    is_token_blacklisted,
    verify_password,
)
from app.db.database import AsyncSessionDep
from app.db.models.users import User
from app.users.services.security import generate_confirm_token
from app.core.config import settings

from app.tasks.tasks import (
    send_change_password,
    send_registration_email,
    send_resend_email_confirmation,
    send_reset_password,
    send_set_password,
)


router = APIRouter(
    prefix="/auth",
    tags=["Аутентификация и авторизация"],
    responses={
        # 401: {'detail': 'string'},
        # 403: {'detail': 'string'},
    },
)

logger = logging.getLogger(__name__)


@router.post(
    "/token",
    summary="Получение jwt-токена",
    description="Получение jwt-токена",
)
async def login(
    session: AsyncSessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
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
        raise HTTPException(
            status_code=400, detail="Пользователь не активирован"
        )

    # Получаем разрешения для роли пользователя
    role = user.role
    role_scopes = await get_role_scopes(role)
    # Формируем список scopes на основе разрешений роли
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "scopes": role_scopes},
        expires_delta=access_token_expires,
    )
    logger.info("Токен успешно выдан пользователю: %s", user.email)
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
    if form_data.password != form_data.repeat_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароли не совпадают",
        )
    # is_exists = await session.scalar(
    #     select(exists().where(User.email == form_data.email))
    # )
    # if is_exists:
    #     raise HTTPException(
    #         status_code=400, detail="Пользователь с таким email существует"
    #     )
    user_db = User(
        **form_data.model_dump(exclude={"password", "repeat_password"})
    )
    user_db.hashed_password = get_password_hash(form_data.password)
    confirm_token = generate_confirm_token(user_db.email)
    user_db.email_confirm_token = confirm_token
    session.add(user_db)
    await session.commit()
    logger.info("Регистрация пользовтаеля %s прошла успешно", user_db.email)
    send_registration_email.delay(
        confirm_token, user_db.email, user_db.first_name, form_data.password
    )
    return RegisterUserPublic.model_validate(user_db)


@router.get("/users/me")
async def read_users_me(
    current_user: Annotated[
        User, Security(get_current_user, scopes=["me:read"])
    ],
):
    return RegisterUserPublic.model_validate(current_user)


@router.post("/logout", summary="Аннулирование токена")
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    redis: Annotated[Redis, Depends(get_blacklist_tokens_redis_client)],
):
    """Аннулирование токена: добавление в чёрный список"""
    if not token or await is_token_blacklisted(token, redis):
        raise HTTPException(
            status_code=400, detail="Токен не активен либо отсутствует"
        )
    await redis.setex(
        f"blacklist:{token}", 3600, "blacklisted"
    )  # TTL 60 минут
    logger.info("Токен %s аннулирован", token)
    return JSONResponse(
        status_code=200, content={"message": "Токен аннулирован"}
    )


@router.get(
    "/confirm_email",
    summary="Подтверждение email пользователя "
    "(вызывается по ссылке из письма)",
    description="Подтверждение email пользователя "
    "(вызывается по ссылке из письма)",
)
async def confirm_email(token: str, session: AsyncSessionDep):
    """Подтверждение email пользователя"""
    query = select(User).where(User.email_confirm_token == token)
    user = await session.scalar(query)
    if not user:
        raise HTTPException(status_code=400, detail="Невалидный токен")
    confirm_time = user.email_confirm_time
    if confirm_time is None:
        raise HTTPException(status_code=400, detail="Невалидный токен")
    if confirm_time < datetime.now(UTC) - timedelta(
        minutes=settings.EMAIL_CONFIRMATION_TOKEN_EXPIRE_MINUTES
    ):
        user.email_confirm_token = None
        user.email_confirm_time = None
        session.add(user)
        await session.commit()
        raise HTTPException(status_code=400, detail="Невалидный токен")
    user.is_email_confirmed = True
    user.email_confirm_token = None
    user.email_confirm_time = None
    session.add(user)
    await session.commit()
    logger.info("Выполнено подтверждение email %s пользователя", user.email)
    return JSONResponse(
        status_code=200, content={"message": "Email подтвержден"}
    )


@router.post(
    "/resend_email_confirmation",
    summary="Отправка повторного письма для подтверждения email",
    description="Отправка повторного письма для подтверждения email",
)
async def resend_email_confirmation(
    current_user: Annotated[User | None, Depends(get_current_user)],
    session: AsyncSessionDep,
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Необходима авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if current_user.is_email_confirmed:
        raise HTTPException(status_code=400, detail="Email уже подтвержден")
    token = generate_confirm_token(current_user.email)
    current_user.email_confirm_token = token
    current_user.email_confirm_time = datetime.now(UTC)
    session.add(current_user)
    await session.commit()
    logger.info(
        "Отправлено эл.письмо о подтверждении email %s", current_user.email
    )
    send_resend_email_confirmation.delay(
        token, current_user.email, current_user.first_name
    )
    return JSONResponse(
        status_code=200,
        content={
            "message": "Письмо о повторном подтверждении email отправлено"
        },
    )


@router.post(
    "/change_password",
    summary="Смена пароля",
    description="Смена пароля",
)
async def change_password(
    form_data: Annotated[ChangePassword, Form()],
    session: AsyncSessionDep,
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_blacklist_tokens_redis_client)],
    token: Annotated[str, Depends(oauth2_scheme)],
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Необходима авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )
    is_password_correct = verify_password(
        form_data.old_password, current_user.hashed_password
    )
    if not is_password_correct:
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")

    if form_data.new_password != form_data.repeat_password:
        raise HTTPException(status_code=400, detail="Пароли не совпадают")

    # Проверка сложности пароля
    if len(form_data.new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Пароль должен содержать минимум 8 символов",
        )

    # Проверка, что новый пароль отличается от старого
    if verify_password(form_data.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="Новый пароль должен отличаться от текущего",
        )

    # Изменение пароля
    current_user.hashed_password = get_password_hash(form_data.new_password)
    session.add(current_user)
    await session.commit()

    # Аннулирование текущего токена
    await redis.setex(
        f"blacklist:{token}",
        settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "blacklisted",
    )

    # Создание нового токена
    new_token = create_access_token(
        data={
            "sub": current_user.email,
            "scopes": await get_role_scopes(current_user.role),
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    logger.info("Пароль пользователя %s успешно изменен", current_user.email)
    # Отправка уведомления о смене пароля
    send_change_password.delay(
        current_user.email, form_data.new_password, current_user.first_name
    )
    return JSONResponse(
        status_code=200,
        content={
            "message": "Пароль успешно изменен",
            "access_token": new_token,
            "token_type": "bearer",
        },
    )


@router.post(
    "/password-reset",
    summary="Сброс пароля",
    description="Сброс пароля",
)
async def password_reset(
    email: Annotated[str, Form()],
    session: AsyncSessionDep,
):
    user = await session.scalar(select(User).where(User.email == email))

    # Проверяем, что пользователь существует, но не сообщаем об этом клиенту
    if not user:
        return JSONResponse(
            status_code=200,
            content={
                "message": "Если указанный email зарегистрирован, на него отправлено письмо для сброса пароля"
            },
        )

    # Проверяем, что email был подтвержден
    if not user.is_email_confirmed:
        return JSONResponse(
            status_code=200,
            content={
                "message": "Если указанный email зарегистрирован, "
                "на него отправлено письмо для сброса пароля"
            },
        )

    # Генерируем токен для сброса пароля
    token = generate_confirm_token(email)
    user.password_reset_token = token
    user.password_reset_time = datetime.now(UTC)
    session.add(user)
    await session.commit()
    logger.info("Отправлено эл. письмо для сброса пароля email: %s", email)
    # Отправляем письмо для сброса пароля
    send_reset_password.delay(email, token)

    return JSONResponse(
        status_code=200,
        content={
            "message": "Если указанный email зарегистрирован, "
            "на него отправлено письмо для сброса пароля"
        },
    )


@router.get(
    "/reset_password_confirm",
    summary="Подтверждение токена для сброса пароля",
    description="Подтверждение токена для сброса пароля",
)
async def reset_password_confirm(
    email: str,
    token: str,
    session: AsyncSessionDep,
):
    user = await session.scalar(select(User).where(User.email == email))
    if not user:
        raise HTTPException(status_code=400, detail="Пользователь не найден")

    def clear_token():
        user.password_reset_token = None
        user.password_reset_time = None
        session.add(user)

    # Проверка валидности токена
    if not user.password_reset_token or not user.password_reset_time:
        clear_token()
        await session.commit()
        raise HTTPException(
            status_code=400, detail="Токен сброса пароля не найден"
        )

    if user.password_reset_token != token:
        clear_token()
        await session.commit()
        raise HTTPException(
            status_code=400, detail="Недействительный токен сброса пароля"
        )

    # Проверка времени действия токена
    if user.password_reset_time < datetime.now(UTC) - timedelta(
        minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    ):
        clear_token()
        await session.commit()
        raise HTTPException(
            status_code=400, detail="Срок действия токена истек"
        )
    logger.info("Токен сброса пароля %s подтвержден", email)
    return JSONResponse(
        status_code=200,
        content={
            "message": "Токен подтвержден, можно устанавливать новый пароль",
            "email": email,
            "token": token,
        },
    )


@router.post(
    "/set_password",
    summary="Установка нового пароля",
    description="Установка нового пароля",
)
async def set_password(
    form_data: Annotated[SetPassword, Form()],
    session: AsyncSessionDep,
    redis: Annotated[Redis, Depends(get_blacklist_tokens_redis_client)],
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
):
    user = await session.scalar(
        select(User).where(User.email == form_data.email)
    )
    if not user:
        raise HTTPException(status_code=400, detail="Пользователь не найден")

    # Проверка валидности токена
    if (
        not user.password_reset_time
        or user.password_reset_token != form_data.token
    ):
        raise HTTPException(
            status_code=400, detail="Недействительный токен сброса пароля"
        )

    # Проверка срока действия токена
    if user.password_reset_time < datetime.now(UTC) - timedelta(
        minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    ):
        user.password_reset_token = None
        user.password_reset_time = None
        session.add(user)
        await session.commit()
        raise HTTPException(
            status_code=400, detail="Срок действия токена истек"
        )

    # Проверка совпадения паролей
    if form_data.password != form_data.repeat_password:
        raise HTTPException(status_code=400, detail="Пароли не совпадают")

    # Проверка сложности пароля
    if len(form_data.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Пароль должен содержать минимум 8 символов",
        )

    # Установка нового пароля
    user.hashed_password = get_password_hash(form_data.password)
    user.password_reset_token = None
    user.password_reset_time = None
    session.add(user)
    await session.commit()

    if token:
        await redis.setex(
            f"blacklist:{token}",
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "blacklisted",
        )

    # Создание нового токена для авторизации
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "scopes": await get_role_scopes(user.role)},
        expires_delta=access_token_expires,
    )
    logger.info("Новый пароль успешно установлен для %s", user.email)
    send_set_password.delay(user.email, form_data.password, user.first_name)

    return JSONResponse(
        status_code=200,
        content={
            "message": "Пароль успешно установлен",
            "access_token": access_token,
            "token_type": "bearer",
        },
    )

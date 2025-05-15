from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from starlette.status import HTTP_403_FORBIDDEN

from app.api.utils import get_logger, get_user_by_email
from app.core.config import settings
from app.modules.store_interface import RedisStore, StoreProtocol
from app.modules.test_store import TestStore
from app.modules.tlogger import TLogger
from app.schemas import TokenData, User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/user/login", auto_error=False
)


def get_user_store(logger: TLogger = Depends(get_logger)) -> StoreProtocol:
    """
    Get the redis store for users.
    """
    return RedisStore(
        logger, "user", host=settings.REDIS_ADDRESS, port=settings.REDIS_PORT
    )

def get_test_store(logger: TLogger = Depends(get_logger)) -> StoreProtocol:
    """
    Get the redis store for tests.
    """
    return TestStore(RedisStore(
        logger, "tests", host=settings.REDIS_ADDRESS, port=settings.REDIS_PORT
    ))

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_store: StoreProtocol = Depends(get_user_store),
    logger: TLogger = Depends(get_logger),
):
    """
    Get the current user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    unorthorized_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise unorthorized_exception

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        logger.info(f"email: {email}")
        token_data = TokenData(email=email)
    except JWTError as e:
        logger.error(f"JWTError: {e}")
        raise credentials_exception
    user = get_user_by_email(token_data.email, user_store)
    logger.info(
        f"user : {user.full_name}, email: {user.email}, disabled: {user.disabled}"
    )
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get the current active user.
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_user_safe(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_store: StoreProtocol = Depends(get_user_store),
    logger: TLogger = Depends(get_logger),
) -> Optional[User]:
    if token is None:
        return None

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email = payload.get("sub")
        if email is None:
            return None

        logger.info(f"email: {email}")

        token_data = TokenData(email=email)
    except:
        return None

    user = get_user_by_email(token_data.email, user_store)

    logger.info(
        f"user : {user.full_name}, email: {user.email}, disabled: {user.disabled}"
    )

    return user

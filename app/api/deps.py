from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status, Path
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from starlette.status import HTTP_403_FORBIDDEN

from app.api.utils import get_logger, get_user_by_email
from app.core.config import settings
from app.modules.store_interface import RedisStore, StoreProtocol
from app.modules.tests_store import MyTestStore
from app.modules.tlogger import TLogger
from app.schemas import TokenData, User
from app.modules.executions_store import ExecutedTestStore
from app.modules.user_store import UserStore
from app.modules.group_store import GroupStore

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/user/login", auto_error=False
)


def get_user_store(logger: TLogger = Depends(get_logger)) -> UserStore:
    """
    Get the user store with group-based structure.
    """
    redis_store = RedisStore(
        logger, "user", host=settings.REDIS_ADDRESS, port=settings.REDIS_PORT
    )
    return UserStore(redis_store)


def get_group_store(logger: TLogger = Depends(get_logger)) -> GroupStore:
    """
    Get the group store.
    """
    redis_store = RedisStore(
        logger, "group", host=settings.REDIS_ADDRESS, port=settings.REDIS_PORT
    )
    return GroupStore(redis_store)


def get_test_store(logger: TLogger = Depends(get_logger)) -> MyTestStore:
    """
    Get the redis store for tests.
    """
    return MyTestStore(RedisStore(
        logger, "tests", host=settings.REDIS_ADDRESS, port=settings.REDIS_PORT
    ))


def get_execution_store(logger: TLogger = Depends(get_logger)) -> ExecutedTestStore:
    """
    Get test execution store instance.
    """
    return ExecutedTestStore(RedisStore(
        logger, "execution", host=settings.REDIS_ADDRESS, port=settings.REDIS_PORT
    ))

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_store: UserStore = Depends(get_user_store),
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
        logger.info(f"get current useremail: {email}")
        token_data = TokenData(email=email)
    except JWTError as e:
        logger.error(f"JWTError: {e}")
        raise credentials_exception
    
    user = user_store.get_by_email(token_data.email)
    logger.info(
        f"username : {user.full_name}, email: {user.email}, id: {user.id}, disabled: {user.disabled}"
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
    user_store: UserStore = Depends(get_user_store),
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

    user = user_store.get_by_email(token_data.email)

    logger.info(
        f"user : {user.full_name}, email: {user.email}, disabled: {user.disabled}"
    )

    return user

def lookup_user(user_id: str, user_store: UserStore = Depends(get_user_store)):
    """Lookup user by ID across all groups."""
    return user_store.get_by_id_only(user_id)

def lookup_user_by_group_and_id(group_id: str, user_id: str, user_store: UserStore = Depends(get_user_store)):
    """Lookup user by group ID and user ID."""
    return user_store.get(group_id, user_id)

def lookup_test(test_id: str, test_store: StoreProtocol = Depends(get_test_store)):
    return test_store.get(test_id)

def lookup_execution(execution_id: str, execution_store: StoreProtocol = Depends(get_execution_store)):
    return execution_store.get(execution_id)

def lookup_user_by_email(email: str, user_store: UserStore = Depends(get_user_store)):
    return user_store.get_by_email(email.lower())

def owner_or_admin_for_user(
    resource_getter: callable,
):
    async def checker(
        user_id: str = Path(...),
        current_user: User = Depends(get_current_user),
        user_store: UserStore = Depends(get_user_store),
    ):
        resource = resource_getter(user_id, user_store)

        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not found"
            )

        if hasattr(resource, "owner_id"):
            if resource.owner_id != str(current_user.id) and current_user.role != "admin":
                raise HTTPException(status_code=403, detail="Access denied")
        else:
            if str(resource.id) != str(current_user.id) and current_user.role != "admin":
                raise HTTPException(status_code=403, detail="Access denied")

        return resource
    return checker

def owner_or_admin_for_user_by_email(
    resource_getter: callable,
):
    async def checker(
        email: str = Path(...),
        current_user: User = Depends(get_current_user),
        user_store: UserStore = Depends(get_user_store),
    ):
        resource = resource_getter(email, user_store)
        
        if resource is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not found"
            )
            
        if hasattr(resource, "owner_id"):
            if resource.owner_id != str(current_user.id) and current_user.role != "admin":
                raise HTTPException(status_code=403, detail="Access denied")
        if str(current_user.id) == str(resource.id) or current_user.role == "admin":
            return resource
            
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
        
    return checker

def owner_or_admin_for_test(
    resource_getter: callable,
):
    async def checker(
        test_id: str = Path(...),
        current_user: User = Depends(get_current_user),
        test_store: StoreProtocol = Depends(get_test_store),
    ):
        resource = resource_getter(test_id, test_store)

        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test not found"
            )

        # Check if user is admin or belongs to the same group as the test
        if current_user.role == "admin":
            return resource
            
        if resource.group_id == current_user.group:
            return resource

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Test does not belong to your group"
        )
    return checker
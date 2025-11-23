from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status, Path, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from starlette.status import HTTP_403_FORBIDDEN

from app.api.utils import get_logger, get_user_by_email
from app.core.config import settings
from app.core.database import get_db
from app.modules.store_interface import RedisStore, StoreProtocol
from app.modules.sql_store import SQLStore
from app.models import User as UserModel, Group as GroupModel, AITest as AITestModel, TestExecution as TestExecutionModel, Prompt as PromptModel, PromptCategory as PromptCategoryModel, AIConfiguration as AIConfigModel
from sqlalchemy.orm import Session
from app.modules.tests_store import AITestStore
from app.modules.tlogger import TLogger
from app.schemas import TokenData
from app.schemas.user import User
from app.modules.executions_store import ExecutedTestStore
from app.modules.user_store import UserStore
from app.modules.group_store import GroupStore
from app.modules.reports_store import ReportsStore
from app.modules.prompts_store import PromptCategoryStore, PromptStore, PromptSetStore
from app.modules.configurations_store import AIConfigurationStore, AIProviderService
from app.modules.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    RateLimitStrategy,
    InMemoryRateLimitBackend,
    RedisRateLimitBackend,
    RateLimitResult,
)


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/user/login", auto_error=False
)


def get_user_store(
    logger: TLogger = Depends(get_logger),
    db: Session = Depends(get_db)
) -> UserStore:
    """
    Get the user store with PostgreSQL backend.
    """
    sql_store = SQLStore(db, UserModel.__table__, logger)
    return UserStore(sql_store)


def get_group_store(
    logger: TLogger = Depends(get_logger),
    db: Session = Depends(get_db)
) -> GroupStore:
    """
    Get the group store with PostgreSQL backend.
    """
    sql_store = SQLStore(db, GroupModel.__table__, logger)
    return GroupStore(sql_store)


def get_test_store(
    logger: TLogger = Depends(get_logger),
    db: Session = Depends(get_db)
) -> AITestStore:
    """
    Get the PostgreSQL store for tests.
    """
    sql_store = SQLStore(db, AITestModel.__table__, logger)
    return AITestStore(sql_store)


def get_execution_store(
    logger: TLogger = Depends(get_logger),
    db: Session = Depends(get_db)
) -> ExecutedTestStore:
    """
    Get test execution store instance with PostgreSQL backend.
    """
    sql_store = SQLStore(db, TestExecutionModel.__table__, logger)
    return ExecutedTestStore(sql_store)


def get_reports_store(
    logger: TLogger = Depends(get_logger),
    test_store: AITestStore = Depends(get_test_store),
    execution_store: ExecutedTestStore = Depends(get_execution_store),
) -> ReportsStore:
    """
    Get the reports store instance.
    """
    return ReportsStore(test_store, execution_store)

# Dependency to get stores
def get_category_store(
    logger: TLogger = Depends(get_logger),
    db: Session = Depends(get_db)
) -> PromptCategoryStore:
    sql_store = SQLStore(db, PromptCategoryModel.__table__, logger)
    return PromptCategoryStore(sql_store)

def get_prompt_store(
    logger: TLogger = Depends(get_logger),
    db: Session = Depends(get_db)
) -> PromptStore:
    sql_store = SQLStore(db, PromptModel.__table__, logger)
    return PromptStore(sql_store)

def get_prompt_set_store(
    logger: TLogger = Depends(get_logger),
    db: Session = Depends(get_db)
) -> PromptSetStore:
    # Note: PromptSetStore might need a separate table - for now using Prompt table
    sql_store = SQLStore(db, PromptModel.__table__, logger)
    return PromptSetStore(sql_store)

# Dependency to get configuration store
def get_config_store(
    logger: TLogger = Depends(get_logger),
    db: Session = Depends(get_db)
) -> AIConfigurationStore:
    sql_store = SQLStore(db, AIConfigModel.__table__, logger)
    return AIConfigurationStore(sql_store)

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
        f"Full name : {user.full_name}, email: {user.email}, id: {user.id}, disabled: {user.disabled}"
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


# ============================================================================
# Rate Limiting
# ============================================================================

# Global rate limiter instance (initialized lazily)
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Get the global rate limiter instance.
    Initializes with Redis or in-memory backend based on settings.
    """
    global _rate_limiter

    if _rate_limiter is None:
        if settings.RATE_LIMIT_USE_REDIS:
            try:
                import redis
                redis_client = redis.Redis(
                    host=settings.REDIS_ADDRESS,
                    port=settings.REDIS_PORT,
                    decode_responses=True
                )
                # Test connection
                redis_client.ping()
                backend = RedisRateLimitBackend(redis_client)
            except Exception:
                # Fallback to in-memory if Redis unavailable
                backend = InMemoryRateLimitBackend()
        else:
            backend = InMemoryRateLimitBackend()

        _rate_limiter = RateLimiter(backend)

        # Configure endpoint-specific rate limits from settings
        _rate_limiter.configure_endpoint(
            "login",
            RateLimitConfig(
                requests=settings.RATE_LIMIT_LOGIN_REQUESTS,
                window_seconds=settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS,
                block_seconds=settings.RATE_LIMIT_LOGIN_BLOCK_SECONDS,
                strategy=RateLimitStrategy.IP
            )
        )
        _rate_limiter.configure_endpoint(
            "registration",
            RateLimitConfig(
                requests=settings.RATE_LIMIT_REGISTRATION_REQUESTS,
                window_seconds=settings.RATE_LIMIT_REGISTRATION_WINDOW_SECONDS,
                block_seconds=settings.RATE_LIMIT_REGISTRATION_BLOCK_SECONDS,
                strategy=RateLimitStrategy.IP
            )
        )
        _rate_limiter.configure_endpoint(
            "password_reset",
            RateLimitConfig(
                requests=settings.RATE_LIMIT_PASSWORD_RESET_REQUESTS,
                window_seconds=settings.RATE_LIMIT_PASSWORD_RESET_WINDOW_SECONDS,
                block_seconds=settings.RATE_LIMIT_PASSWORD_RESET_BLOCK_SECONDS,
                strategy=RateLimitStrategy.IP
            )
        )
        _rate_limiter.configure_endpoint(
            "ai_connection_test",
            RateLimitConfig(
                requests=settings.RATE_LIMIT_AI_TEST_REQUESTS,
                window_seconds=settings.RATE_LIMIT_AI_TEST_WINDOW_SECONDS,
                block_seconds=settings.RATE_LIMIT_AI_TEST_BLOCK_SECONDS,
                strategy=RateLimitStrategy.IP_ENDPOINT
            )
        )

    return _rate_limiter


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, considering proxy headers."""
    # Check for forwarded headers (in case of reverse proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Get the first IP in the chain (original client)
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fallback to direct client
    if request.client:
        return request.client.host

    return "unknown"


def create_rate_limit_dependency(endpoint_name: str):
    """
    Factory to create rate limit dependencies for specific endpoints.

    Usage:
        @router.post("/login")
        async def login(
            rate_limit: None = Depends(create_rate_limit_dependency("login")),
            ...
        ):
    """
    async def rate_limit_check(
        request: Request,
        logger: TLogger = Depends(get_logger),
    ) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return None

        rate_limiter = get_rate_limiter()
        client_ip = get_client_ip(request)

        result = rate_limiter.check(
            endpoint=endpoint_name,
            ip=client_ip
        )

        if not result.allowed:
            logger.warning(
                f"Rate limit exceeded for {endpoint_name}: IP={client_ip}, "
                f"retry_after={result.retry_after}s"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Please try again in {result.retry_after} seconds.",
                headers={
                    "Retry-After": str(result.retry_after),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(result.reset_time))
                }
            )

        return None

    return rate_limit_check


# Pre-built rate limit dependencies for common endpoints
rate_limit_login = create_rate_limit_dependency("login")
rate_limit_registration = create_rate_limit_dependency("registration")
rate_limit_password_reset = create_rate_limit_dependency("password_reset")
rate_limit_ai_test = create_rate_limit_dependency("ai_connection_test")
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from uuid import uuid4
from jose import JWTError, jwt

import app.main as server
from app.modules.store_interface import LocalStore
from app.modules.user_store import UserStore
from app.modules.group_store import GroupStore
from app.schemas import User, GroupCreate
from app.core.config import settings


class ForceEquals:
    def __eq__(self, other):
        return True



@pytest.fixture(autouse=True)
def setup_and_teardown(request: pytest.FixtureRequest):
    # Only apply this fixture to test classes that need FastAPI app setup
    # Skip for unit test classes that don't use the app
    test_class_name = request.instance.__class__.__name__ if request.instance else ""
    
    # Skip for pure unit test classes
    if test_class_name in ["TestAIConnectionService"]:
        yield
        return
    
    # Setup
    request.instance.app = server.app  # type: ignore
    request.instance.client = TestClient(server.app)  # type: ignore
    request.instance.user_store = UserStore(LocalStore())  # type: ignore
    request.instance.group_store = GroupStore(LocalStore())  # type: ignore
    request.instance.force_equals = ForceEquals()  # type: ignore
    request.instance.valid_passwords = ["passworD1!", "newPassworD8("]  # type: ignore
    
    # Set up dependency overrides
    from app.api import deps
    request.instance.app.dependency_overrides[deps.get_user_store] = lambda: request.instance.user_store  # type: ignore
    request.instance.app.dependency_overrides[deps.get_group_store] = lambda: request.instance.group_store  # type: ignore

    yield

    # Teardown
    request.instance.app.dependency_overrides = {}  # type: ignore
    # Clean up user store by getting all keys from the underlying store
    underlying_store = request.instance.user_store._store  # type: ignore
    keys = underlying_store.keys()  # type: ignore
    for key in keys:  # type: ignore
        underlying_store.pop(key)  # type: ignore
    
    # Clean up group store by getting all keys from the underlying store
    group_underlying_store = request.instance.group_store._store  # type: ignore
    group_keys = group_underlying_store.keys()  # type: ignore
    for key in group_keys:  # type: ignore
        group_underlying_store.pop(key)  # type: ignore


@pytest.fixture
def test_user():
    """Create a test user object."""
    return User(
        id=uuid4(),
        email="goricoaico+fixture@gmail.com",
        full_name="Test User",
        disabled=False,
        created_at=datetime.now(timezone.utc),
        is_verified=True,
        group=str(uuid4())
    )

@pytest.fixture
def test_user_token(test_user):
    """Create a test user and return a valid JWT token for authentication."""
    from app.api import deps
    from app.modules.prompts_store import PromptCategoryStore, PromptStore, PromptSetStore
    from app.modules.configurations_store import AIConfigurationStore
    import app.main as main_app
    
    # Override authentication to return our test user
    main_app.app.dependency_overrides[deps.get_current_active_user] = lambda: test_user
    
    # Override store dependencies to use LocalStore instead of Redis
    main_app.app.dependency_overrides[deps.get_category_store] = lambda: PromptCategoryStore(LocalStore())
    main_app.app.dependency_overrides[deps.get_prompt_store] = lambda: PromptStore(LocalStore())
    main_app.app.dependency_overrides[deps.get_prompt_set_store] = lambda: PromptSetStore(LocalStore())
    main_app.app.dependency_overrides[deps.get_config_store] = lambda: AIConfigurationStore(LocalStore())
    
    # Create test user data for JWT token
    user_data = {
        "sub": test_user.email,
        "user_id": str(test_user.id),
        "exp": datetime.now(timezone.utc).timestamp() + 3600  # 1 hour from now
    }
    
    # Create JWT token
    token = jwt.encode(user_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    yield token
    
    # Clean up the overrides after the test
    main_app.app.dependency_overrides.clear()

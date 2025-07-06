import pytest
from fastapi.testclient import TestClient

import app.main as server
from app.modules.store_interface import LocalStore
from app.modules.user_store import UserStore
from app.modules.group_store import GroupStore


class ForceEquals:
    def __eq__(self, other):
        return True



@pytest.fixture(autouse=True)
def setup_and_teardown(request: pytest.FixtureRequest):
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

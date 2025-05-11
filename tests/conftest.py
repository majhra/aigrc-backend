import pytest
from fastapi.testclient import TestClient

import app.main as server
from app.modules.store_interface import LocalStore


class ForceEquals:
    def __eq__(self, other):
        return True



@pytest.fixture(autouse=True)
def setup_and_teardown(request: pytest.FixtureRequest):
    # Setup
    request.instance.app = server.app  # type: ignore
    request.instance.client = TestClient(server.app)  # type: ignore
    request.instance.user_store = LocalStore()  # type: ignore
    request.instance.force_equals = ForceEquals()  # type: ignore
    request.instance.valid_passwords = ["passworD1!", "newPassworD8("]  # type: ignore
    
    # Set up dependency override for user_store
    from app.api import deps
    request.instance.app.dependency_overrides[deps.get_user_store] = lambda: request.instance.user_store  # type: ignore

    yield

    # Teardown
    request.instance.app.dependency_overrides = {}  # type: ignore
    keys = request.instance.user_store.keys()  # type: ignore
    for key in keys:  # type: ignore
        request.instance.user_store.pop(key)  # type: ignore

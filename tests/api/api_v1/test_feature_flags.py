from fastapi import status
from UnleashClient import UnleashClient

from app.api import deps
from app.api.utils import get_unleash_client
from app.core.config import settings
from app.schemas import User


class MockUnleashClient(UnleashClient):
    def __init__(self, features, variants):
        self.features = features
        self.variants = variants

    def get_variant(self, flag, context):
        return self.variants[flag]


class TestFeatureFlags:
    def test_proxy_success(self, request):
        app = request.instance.app

        features = ["test"]
        variants = {
            "test": {
                "name": "disabled",
                "enabled": True,
                "feature_enabled": True,
            }
        }
        mocked_unleash_client = MockUnleashClient(features, variants)

        app.dependency_overrides[deps.get_current_user_safe] = lambda: User(
            email="goricoaico@gmail.com",
            password=request.instance.valid_passwords[0],
        )

        app.dependency_overrides[get_unleash_client] = lambda: mocked_unleash_client

        response = request.instance.client.get(
            f"{settings.API_V1_STR}/feature_flags/proxy"
        )

        expected_response = {
            "toggles": [
                {
                    "name": "test",
                    "enabled": True,
                    "variant": {"name": "disabled", "enabled": True},
                }
            ]
        }

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_response

    def test_proxy_not_configured(self, request):
        app = request.instance.app

        app.dependency_overrides[deps.get_current_user_safe] = lambda: User(
            email="goricoaico@gmail.com",
            password=request.instance.valid_passwords[0],
        )

        app.dependency_overrides[get_unleash_client] = lambda: None

        response = request.instance.client.get(
            f"{settings.API_V1_STR}/feature_flags/proxy"
        )

        expected_response = {
            "detail": "Unleash client not configured",
        }

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json() == expected_response

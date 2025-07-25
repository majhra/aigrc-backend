from datetime import datetime, timedelta, timezone
from unittest.mock import patch, Mock
import uuid
import pytest
from typing import Any

from fastapi import status
from pydantic import UUID4

from app.api import deps
# Removed direct import to allow mocking to work properly
from app.core.config import settings
from app.schemas import User

from app.api import utils
from app.api.utils import (
    create_access_token,
    get_user_by_email,
)

# Mock password hashing for fast tests - use real bcrypt with low cost for speed
def mock_get_password_hash(password: str) -> str:
    """Fast hash for testing using bcrypt with low cost factor"""
    import bcrypt
    # Use cost factor 4 instead of default 12 for much faster hashing in tests
    salt = bcrypt.gensalt(rounds=4)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def mock_verify_password(plain_password: str, hashed_password: str) -> bool:
    """Fast verification for testing using real bcrypt"""
    import bcrypt
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# Apply mocks at module level for fast password operations
password_hash_mock = patch('app.api.utils.get_password_hash', side_effect=mock_get_password_hash)
verify_password_mock = patch('app.api.utils.verify_password', side_effect=mock_verify_password)

# Start all mocks
password_hash_mock.start()
verify_password_mock.start()

# Cleanup function to stop mocks when module is unloaded
import atexit
def cleanup_mocks():
    password_hash_mock.stop()
    verify_password_mock.stop()

atexit.register(cleanup_mocks)

class UUIDMatcher:
    """A matcher that accepts any valid UUID4 string."""
    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False
        try:
            # Try to parse as UUID4
            uuid_obj = uuid.UUID(str(other))
            return uuid_obj.version == 4
        except (ValueError, AttributeError):
            return False


class TestUser:
    def setup_method(self):
        self.uuid_matcher = UUIDMatcher()

    @patch("app.api.api_v1.endpoints.user.send_verification_email")
    def test_signup_success(self, mock_send_verification_email, request):
        client = request.instance.client
        force_equals = request.instance.force_equals
        user_store = request.instance.user_store

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )

        data = {
            "email": "gorocoaico+test_signup_success@gmail.com",
            "password": request.instance.valid_passwords[0],
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/register", data=data, headers=headers
        )

        expected_response = {
            'id': self.uuid_matcher,
            "email": "gorocoaico+test_signup_success@gmail.com",
            "full_name": None,
            "disabled": False,
            "created_at": force_equals,
            "last_login": None,
            "is_verified": False,
            'group': force_equals
        }

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['data'] == expected_response

    def test_signup_user_already_exists(self, request):
        user_store = request.instance.user_store
        client = request.instance.client

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )

        password_plain_text = request.instance.valid_passwords[0]
        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico+test_signup_user_already_exists@gmail.com",
            "full_name": None,
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": False,
            "verification_code": "FGD69G",
            "verification_code_expires_at": (
                datetime.now() + timedelta(days=10)
            ).replace(tzinfo=timezone.utc),
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])

        data = {"email": user["email"], "password": password_plain_text}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/register", data=data, headers=headers
        )

        expected_response = {"detail": "Bad Request"}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_response

    @patch("app.api.api_v1.endpoints.user.send_verification_email")
    def test_signup_failed_to_send_verification_email(
        self, mock_send_verification_email, request
    ):
        client = request.instance.client
        user_store = request.instance.user_store

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )

        error_message = "Failed to send verification email"
        email_exception = Exception(error_message)
        email_exception.message = error_message
        mock_send_verification_email.side_effect = email_exception

        data = {
            "email": "gorocoaico+test_signup_failed_to_send_verification_email@gmail.com",
            "password": request.instance.valid_passwords[0],
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/register", data=data, headers=headers
        )

        expected_response = {"detail": error_message}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_response

    @patch("app.modules.email_service.EmailService")
    def test_signup_missing_password(self, mock_email_service, request):
        client = request.instance.client
        force_equals = request.instance.force_equals
        user_store = request.instance.user_store

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )

        data = {"email": "gorocoaico+test_signup_missing_password@gmail.com"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/register", data=data, headers=headers
        )

        expected_response = {
            "detail": [
                {
                    "type": "missing",
                    "loc": ["body", "password"],
                    "msg": "Field required",
                    "input": None,
                    "url": force_equals,
                }
            ]
        }

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.json() == expected_response

    def test_login_success(self, request):
        user_store = request.instance.user_store
        client = request.instance.client
        force_equals = request.instance.force_equals

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )

        password_plain_text = request.instance.valid_passwords[0]
        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": True,
            "verification_code": None,
            "verification_code_expires_at": None,
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])


        data = {"username": user["email"], "password": password_plain_text}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/login", data=data, headers=headers
        )

        expected_response = {"access_token": force_equals, "token_type": "bearer"}
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_response

    def test_login_email_not_verified(self, request):
        user_store = request.instance.user_store
        client = request.instance.client

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )

        password_plain_text = request.instance.valid_passwords[0]
        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": False,
            "verification_code": "FGD69G",
            "verification_code_expires_at": (
                datetime.now() + timedelta(days=10)
            ).replace(tzinfo=timezone.utc),
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])

        data = {"username": user["email"], "password": password_plain_text}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/login", data=data, headers=headers
        )

        expected_response = {"detail": "Email is not verified"}
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == expected_response

    def test_login_user_does_not_exist(self, request):
        client = request.instance.client
        user_store = request.instance.user_store

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )

        data = {
            "username": "gorocoaico@gmail.com",
            "password": request.instance.valid_passwords[0],
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/login", data=data, headers=headers
        )

        expected_response = {"detail": "Incorrect username or password"}
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == expected_response

    def test_verify_email_success(self, request):
        force_equals = request.instance.force_equals
        user_store = request.instance.user_store
        client = request.instance.client

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )


        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": request.instance.valid_passwords[0],
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": False,
            "verification_code": "FGD69G",
            "verification_code_expires_at": (
                datetime.now() + timedelta(days=10)
            ).replace(tzinfo=timezone.utc),
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])

        data = {"email": user["email"], "verification_code": user["verification_code"]}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/verify_email", data=data, headers=headers
        )

        expected_response = {"token_type": "bearer", "access_token": force_equals}
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_response


    def test_verify_email_invalid_code(self, request):
        force_equals = request.instance.force_equals
        user_store = request.instance.user_store
        client = request.instance.client

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )


        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": request.instance.valid_passwords[0],
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": False,
            "verification_code": "FGD69G",
            "verification_code_expires_at": (
                datetime.now() + timedelta(days=10)
            ).replace(tzinfo=timezone.utc),
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])

        data = {"email": user["email"], "verification_code": "INVALID"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/verify_email", data=data, headers=headers
        )

        expected_response = {"detail": "Verification code does not match"}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_response

    def test_verify_email_expired_code(self, request):
        user_store = request.instance.user_store
        client = request.instance.client

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )


        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": request.instance.valid_passwords[0],
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": False,
            "verification_code": "FGD69G",
            "verification_code_expires_at": (
                datetime.now() - timedelta(days=10)
            ).replace(tzinfo=timezone.utc),
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])

        data = {"email": user["email"], "verification_code": user["verification_code"]}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/verify_email", data=data, headers=headers
        )

        expected_response = {"detail": "Malformed Data"}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_response

    def test_verify_email_already_verified(self, request):
        user_store = request.instance.user_store
        client = request.instance.client

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )


        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": request.instance.valid_passwords[0],
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": True,
            "verification_code": None,
            "verification_code_expires_at": None,
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])

        data = {"email": user["email"], "verification_code": "FGD69G"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/verify_email", data=data, headers=headers
        )

        expected_response = {"detail": "Malformed Data"}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_response

    def test_verify_email_user_does_not_exist(self, request):
        client = request.instance.client
        user_store = request.instance.user_store

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )


        data = {"email": "gorocoaico@gmail.com", "verification_code": "FGD69G"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/verify_email", data=data, headers=headers
        )

        expected_response = {"detail": "Malformed Data"}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_response

    @patch("app.api.api_v1.endpoints.user.send_verification_email")
    def test_resend_verification_email_success(
        self, mock_send_verification_email, request
    ):
        user_store = request.instance.user_store
        client = request.instance.client

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )

        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": request.instance.valid_passwords[0],
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": False,
            "verification_code": "FGD69G",
            "verification_code_expires_at": (
                datetime.now() + timedelta(days=10)
            ).replace(tzinfo=timezone.utc),
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])

        data = {"email": user["email"]}
        response = client.post(
            f"{settings.API_V1_STR}/user/resend_verification_email", params=data
        )

        expected_response = {"message": "Verification email sent"}
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_response

    def test_resend_verification_email_user_does_not_exist(self, request):
        client = request.instance.client
        user_store = request.instance.user_store

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )

        data = {"email": "gorocoaico@gmail.com"}
        response = client.post(
            f"{settings.API_V1_STR}/user/resend_verification_email", params=data
        )

        expected_response = {"detail": "Malformed Data"}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_response

    @patch("app.api.api_v1.endpoints.user.AWSEmailExecuter")
    @patch("app.api.api_v1.endpoints.user.EmailService")
    def test_support_request_success(
        self, mock_email_service, mock_aws_email_executer, request
    ):
        app = request.instance.app
        client = request.instance.client

        app.dependency_overrides[deps.get_current_user] = lambda: User(
            email="gorocoaico@gmail.com",
            password=request.instance.valid_passwords[0],
        )

        data = {"message": "This is a test support request message."}
        response = client.post(f"{settings.API_V1_STR}/user/support/", params=data)

        expected_response = {"message": "Support request sent"}
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_response

    def test_support_request_unauthorized(self, request):
        client = request.instance.client

        data = {"message": "This is a test support request message."}
        headers = {"Authorization": "Bearer xxxxx.yyyyy.zzzzz"}
        response = client.post(
            f"{settings.API_V1_STR}/user/support/", params=data, headers=headers
        )

        expected_response = {"detail": "Could not validate credentials"}
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == expected_response

    @patch("app.api.api_v1.endpoints.user.AWSEmailExecuter")
    @patch("app.api.api_v1.endpoints.user.EmailService")
    def test_support_request_empty_message(
        self, mock_email_service, mock_aws_email_executer, request
    ):
        app = request.instance.app
        client = request.instance.client

        app.dependency_overrides[deps.get_current_user] = lambda: User(
            email="gorocoaico@gmail.com",
            password=request.instance.valid_passwords[0],
        )

        data = {"message": None}
        response = client.post(f"{settings.API_V1_STR}/user/support/", params=data)

        expected_response = {"detail": "No message provided"}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_response

    @patch("app.api.api_v1.endpoints.user.AWSEmailExecuter")
    @patch("app.api.api_v1.endpoints.user.EmailService")
    def test_support_request_email_failed_to_send(
        self, mock_email_service, mock_aws_email_executer, request
    ):
        app = request.instance.app
        client = request.instance.client

        app.dependency_overrides[deps.get_current_user] = lambda: User(
            email="gorocoaico@gmail.com",
            password=request.instance.valid_passwords[0],
        )

        error_message = "Failed to send support request email"
        email_exception = Exception(error_message)
        email_exception.message = error_message
        mock_email_service.side_effect = email_exception

        data = {"message": "This is a test support request message."}
        response = client.post(f"{settings.API_V1_STR}/user/support/", params=data)

        expected_response = {"detail": "Internal server error - please try again later"}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_response

    @patch("app.api.api_v1.endpoints.user.send_invite_email")
    def test_invite_user_success(self, mock_send_invite_email, request):
        user_store = request.instance.user_store
        group_store = request.instance.group_store
        client = request.instance.client

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )
        request.instance.app.dependency_overrides[deps.get_group_store] = (
            lambda: group_store
        )

        # Create a group first
        from app.schemas import GroupCreate
        group_data = GroupCreate(
            name="Test Team",
            description="Test team for invites"
        )
        group = group_store.create(group_data, "system")
        group_id = str(group.id)

        # Create the inviter user
        password_plain_text = request.instance.valid_passwords[0]
        inviter_user = {
            "id": str(uuid.uuid4()),
            "email": "goricoaico+test_invite_user_success_inviter@gmail.com",
            "full_name": "John Inviter",
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": True,
            "group": group_id
        }
        user_store.create(User(**inviter_user), group_id)

        # Login to get token
        login_data = {"username": inviter_user["email"], "password": password_plain_text}
        login_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        login_response = client.post(
            f"{settings.API_V1_STR}/user/login", data=login_data, headers=login_headers
        )
        token = login_response.json()["access_token"]

        # Mock the invite email function
        mock_send_invite_email.return_value = "INVITE123"

        # Send invite
        invite_data = {"email": "goricoaico+test_invite_user_success_newuser@gmail.com"}
        invite_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {token}"
        }
        response = client.post(
            f"{settings.API_V1_STR}/user/invite", data=invite_data, headers=invite_headers
        )

        expected_response = {
            "message": "Invitation sent successfully",
            "email": "goricoaico+test_invite_user_success_newuser@gmail.com"
        }
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_response

        # Verify the invite email was called with correct parameters
        mock_send_invite_email.assert_called_once_with(
            email="goricoaico+test_invite_user_success_newuser@gmail.com",
            inviter_name="John Inviter",
            group_id=group_id,
            invite_url=settings.INVITE_URL
        )


    def test_invite_user_unauthorized(self, request):
        client = request.instance.client

        invite_data = {"email": "goricoaico+test_invite_user_success_newuser@gmail.com"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/invite", data=invite_data, headers=headers
        )

        expected_response = {"detail": "Not authenticated"}
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == expected_response


    def test_invite_user_already_exists(self, request):
        user_store = request.instance.user_store
        group_store = request.instance.group_store
        client = request.instance.client

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )
        request.instance.app.dependency_overrides[deps.get_group_store] = (
            lambda: group_store
        )

        # Create a group first
        from app.schemas import GroupCreate
        group_data = GroupCreate(
            name="Test Team",
            description="Test team for invites"
        )
        group = group_store.create(group_data, "system")
        group_id = str(group.id)

        # Create the inviter user
        password_plain_text = request.instance.valid_passwords[0]
        inviter_user = {
            "id": str(uuid.uuid4()),
            "email": "goricoaico+test_invite_user_already_exists_inviter@gmail.com",
            "full_name": "John Inviter",
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": True,
            "group": group_id
        }
        user_store.create(User(**inviter_user), group_id)

        # Create the user to be invited (already exists)
        existing_user = {
            "id": str(uuid.uuid4()),
            "email": "goricoaico+test_invite_user_already_exists_existing@gmail.com",
            "full_name": None,
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": True,
            "group": group_id
        }
        user_store.create(User(**existing_user), group_id)

        # Login to get token
        login_data = {"username": inviter_user["email"], "password": password_plain_text}
        login_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        login_response = client.post(
            f"{settings.API_V1_STR}/user/login", data=login_data, headers=login_headers
        )
        token = login_response.json()["access_token"]

        # Try to invite existing user
        invite_data = {"email": "goricoaico+test_invite_user_already_exists_existing@gmail.com"}
        invite_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {token}"
        }
        response = client.post(
            f"{settings.API_V1_STR}/user/invite", data=invite_data, headers=invite_headers
        )

        expected_response = {"detail": "User already exists"}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_response


    def test_invite_user_no_group(self, request):
        user_store = request.instance.user_store
        client = request.instance.client

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )

        # Create user without group
        password_plain_text = request.instance.valid_passwords[0]
        user_without_group = {
            "id": (uuid.uuid4()),
            "email": "goricoaico+test_invite_user_no_group@gmail.com",
            "full_name": "No Group User",
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": True,
            "group": None
        }
        # Create user without a group by using a temporary group that won't be validated
        user_store.create(User(**user_without_group), "temp_group")
        
        # Manually update the user to have no group
        user_without_group["group"] = None
        user_store.update("temp_group", str(user_without_group["id"]), user_without_group)

        # Login to get token
        login_data = {"username": user_without_group["email"], "password": password_plain_text}
        login_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        login_response = client.post(
            f"{settings.API_V1_STR}/user/login", data=login_data, headers=login_headers
        )
        token = login_response.json()["access_token"]

        # Try to invite without group
        invite_data = {"email": "goricoaico+test_invite_user_no_group_newuser@gmail.com"}
        invite_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {token}"
        }
        response = client.post(
            f"{settings.API_V1_STR}/user/invite", data=invite_data, headers=invite_headers
        )

        expected_response = {"detail": "You must be part of a team to send invites"}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_response


    @patch("app.api.api_v1.endpoints.user.send_invite_email")
    def test_invite_user_email_failed_to_send(self, mock_send_invite_email, request):
        user_store = request.instance.user_store
        group_store = request.instance.group_store
        client = request.instance.client

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )
        request.instance.app.dependency_overrides[deps.get_group_store] = (
            lambda: group_store
        )

        # Create a group first
        from app.schemas import GroupCreate
        group_data = GroupCreate(
            name="Test Team",
            description="Test team for invites"
        )
        group = group_store.create(group_data, "system")
        group_id = str(group.id)

        # Create the inviter user
        password_plain_text = request.instance.valid_passwords[0]
        inviter_user = {
            "id": str(uuid.uuid4()),
            "email": "goricoaico+test_invite_user_email_failed_to_send_inviter@gmail.com",
            "full_name": "John Inviter",
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": True,
            "group": group_id
        }
        user_store.create(User(**inviter_user), group_id)

        # Login to get token
        login_data = {"username": inviter_user["email"], "password": password_plain_text}
        login_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        login_response = client.post(
            f"{settings.API_V1_STR}/user/login", data=login_data, headers=login_headers
        )
        token = login_response.json()["access_token"]

        # Mock the invite email function to fail
        error_message = "Failed to send invite email"
        email_exception = Exception(error_message)
        email_exception.message = error_message
        mock_send_invite_email.side_effect = email_exception

        # Try to send invite
        invite_data = {"email": "goricoaico+test_invite_user_email_failed_to_send_inviter_newuser@gmail.com"}
        invite_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {token}"
        }
        response = client.post(
            f"{settings.API_V1_STR}/user/invite", data=invite_data, headers=invite_headers
        )

        expected_response = {"detail": "Failed to send invitation email"}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_response


    def test_me_success(self, request):
        app = request.instance.app
        client = request.instance.client
        group_store = request.instance.group_store

        # Mock the current active user
        test_user = User(
            id=uuid.uuid4(),
            email="gorocoaico@gmail.com",
            full_name="Test User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            last_login=datetime.now(timezone.utc),
            is_verified=True,
            group="test_group"
        )
        
        app.dependency_overrides[deps.get_current_active_user] = lambda: test_user
        app.dependency_overrides[deps.get_group_store] = lambda: group_store

        response = client.get(f"{settings.API_V1_STR}/user/me")

        expected_response = {
            'id': str(test_user.id),
            "email": "gorocoaico@gmail.com",
            "full_name": "Test User",
            "created_at": test_user.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "last_login": test_user.last_login.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "is_verified": True,
            "disabled": False,
            "group": None  # No group data in test
        }
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_response

    def test_me_unauthorized(self, request):
        client = request.instance.client

        response = client.get(f"{settings.API_V1_STR}/user/me")

        expected_response = {"detail": "Not authenticated"}
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == expected_response

    def test_me_items_success(self, request):
        app = request.instance.app
        client = request.instance.client

        app.dependency_overrides[deps.get_current_active_user] = lambda: User(
            email="gorocoaico@gmail.com",
            password=request.instance.valid_passwords[0],
        )

        response = client.get(f"{settings.API_V1_STR}/user/me/items")

        expected_response = [
            {"item_id": "Foo", "owner": "gorocoaico@gmail.com"}
        ]
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_response

    def test_me_items_unauthorized(self, request):
        client = request.instance.client

        response = client.get(f"{settings.API_V1_STR}/user/me/items")

        expected_response = {"detail": "Not authenticated"}
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == expected_response

    def test_update_profile_success(self, request):
        user_store = request.instance.user_store
        client = request.instance.client

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )

        # Create a test user
        password_plain_text = request.instance.valid_passwords[0]
        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico+test_update_profile_success@gmail.com",
            "full_name": "Original Name",
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "last_login": None,
            "is_verified": True,
            "group": "test_group"
        }
        user_store.create(User(**user), user['group'])

        # Login to get token
        login_data = {"username": user["email"], "password": password_plain_text}
        login_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        login_response = client.post(
            f"{settings.API_V1_STR}/user/login", data=login_data, headers=login_headers
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"  # Add content type header
        }

        # Update profile
        update_data = {"full_name": "New Name"}
        response = client.post(
            f"{settings.API_V1_STR}/user/update_profile",
            json=update_data,  # Use json instead of params
            headers=headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Profile updated successfully"}

        # Verify the update
        updated_user = user_store.get_by_email(user["email"])
        assert updated_user.full_name == "New Name"
        assert updated_user.email == user["email"]  # Email should not change
        assert updated_user.group == user["group"]  # Group should not change

    def test_fail_update_profile_with_username(self, request):
        user_store = request.instance.user_store
        client = request.instance.client

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )

        # Create a test user
        password_plain_text = request.instance.valid_passwords[0]
        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico+test_update_profile_username@gmail.com",
            "full_name": None,
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "last_login": None,
            "is_verified": True,
            "group": "test_group"
        }
        user_store.create(User(**user), user['group'])

        # Login to get token
        login_data = {"username": user["email"], "password": password_plain_text}
        login_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        login_response = client.post(
            f"{settings.API_V1_STR}/user/login", data=login_data, headers=login_headers
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Update profile with username field
        update_data = {"username": "New Username"}
        response = client.post(
            f"{settings.API_V1_STR}/user/update_profile",
            json=update_data,
            headers=headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "No fields to update"}

    def test_update_profile_non_updatable_fields(self, request):
        user_store = request.instance.user_store
        client = request.instance.client

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )

        # Create a test user
        password_plain_text = request.instance.valid_passwords[0]
        original_email = "gorocoaico+test_update_profile_fields@gmail.com"
        original_group = "test_group"
        user = {
            "id": str(uuid.uuid4()),
            "email": original_email,
            "full_name": "Original Name",
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "last_login": None,
            "is_verified": True,
            "group": original_group
        }
        user_store.create(User(**user), user['group'])

        # Login to get token
        login_data = {"username": user["email"], "password": password_plain_text}
        login_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        login_response = client.post(
            f"{settings.API_V1_STR}/user/login", data=login_data, headers=login_headers
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try to update non-updatable fields
        update_data = {
            "email": "goricoaico+new.email@gmail.com",
            "group_id": str(uuid.uuid4()),
            "full_name": "New Name"  # This one should update
        }
        response = client.post(
            f"{settings.API_V1_STR}/user/update_profile",
            json=update_data,
            headers=headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Profile updated successfully"}

        # Verify only updatable fields were changed
        updated_user = user_store.get_by_email(original_email)
        assert updated_user.email == original_email  # Email should not change
        assert updated_user.group == original_group  # Group should not change
        assert updated_user.full_name == "New Name"  # This should have updated

    def test_update_profile_to_current_values(self, request):
        user_store = request.instance.user_store
        client = request.instance.client

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )

        # Create a test user
        password_plain_text = request.instance.valid_passwords[0]
        original_name = "Original Name"
        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico+test_update_profile_current@gmail.com",
            "full_name": original_name,
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "last_login": None,
            "is_verified": True,
            "group": "test_group"
        }
        user_store.create(User(**user), user['group'])

        # Login to get token
        login_data = {"username": user["email"], "password": password_plain_text}
        login_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        login_response = client.post(
            f"{settings.API_V1_STR}/user/login", data=login_data, headers=login_headers
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Update profile with current values
        update_data = {"full_name": original_name}
        response = client.post(
            f"{settings.API_V1_STR}/user/update_profile",
            json=update_data,
            headers=headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Profile updated successfully"}

        # Verify the values remain the same
        updated_user = user_store.get_by_email(user["email"])
        assert updated_user.full_name == original_name

    def test_update_profile_empty_data(self, request):
        user_store = request.instance.user_store
        client = request.instance.client

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )

        # Create a test user
        password_plain_text = request.instance.valid_passwords[0]
        original_name = "Original Name"
        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico+test_update_profile_empty@gmail.com",
            "full_name": original_name,
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "last_login": None,
            "is_verified": True,
            "group": "test_group"
        }
        user_store.create(User(**user), user['group'])

        # Login to get token
        login_data = {"username": user["email"], "password": password_plain_text}
        login_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        login_response = client.post(
            f"{settings.API_V1_STR}/user/login", data=login_data, headers=login_headers
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Update profile with empty data
        update_data = {}
        response = client.post(
            f"{settings.API_V1_STR}/user/update_profile",
            json=update_data,
            headers=headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "No fields to update"}

        # Verify nothing changed
        updated_user = user_store.get_by_email(user["email"])
        assert updated_user.full_name == original_name

        # Update profile with ignored data
        update_data = {"not_a_name": "noname", "not_another_field": "not_another_value"}
        response = client.post(
            f"{settings.API_V1_STR}/user/update_profile",
            json=update_data,
            headers=headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "No fields to update"}

        # Verify nothing changed
        updated_user = user_store.get_by_email(user["email"])
        assert updated_user.full_name == original_name

    def test_update_profile_multiple_fields(self, request):
        user_store = request.instance.user_store
        client = request.instance.client

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )

        # Create a test user
        password_plain_text = request.instance.valid_passwords[0]
        new_password = request.instance.valid_passwords[1]
        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico+test_update_profile_multiple@gmail.com",
            "full_name": "Original Name",
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "last_login": None,
            "is_verified": True,
            "group": "test_group"
        }
        user_store.create(User(**user), user['group'])

        # Login to get token
        login_data = {"username": user["email"], "password": password_plain_text}
        login_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        login_response = client.post(
            f"{settings.API_V1_STR}/user/login", data=login_data, headers=login_headers
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Update multiple fields
        update_data = {
            "full_name": "New Name",
            "password": new_password
        }
        response = client.post(
            f"{settings.API_V1_STR}/user/update_profile",
            json=update_data,
            headers=headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Profile updated successfully"}

        # Verify all fields were updated
        updated_user = user_store.get_by_email(user["email"])
        assert updated_user.full_name == "New Name"
        
        # Verify password was updated by trying to login with new password
        new_login_data = {"username": user["email"], "password": new_password}
        new_login_response = client.post(
            f"{settings.API_V1_STR}/user/login", data=new_login_data, headers=login_headers
        )
        assert new_login_response.status_code == status.HTTP_200_OK

    def test_update_profile_unauthenticated(self, request):
        client = request.instance.client

        data = {"full_name": "John Doe"}
        response = client.post(f"{settings.API_V1_STR}/user/update_profile", params=data)

        expected_response = {"detail": "Not authenticated"}
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == expected_response

    @patch("app.api.api_v1.endpoints.user.AWSEmailExecuter")
    @patch("app.api.api_v1.endpoints.user.EmailService")
    def test_password_reset_request_success(
        self, mock_email_service, mock_aws_email_executer, request
    ):
        app = request.instance.app
        client = request.instance.client
        user_store = request.instance.user_store

        app.dependency_overrides[deps.get_user_store] = lambda: user_store

        # Add user to store
        password_plain_text = request.instance.valid_passwords[0]
        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": True,
            "verification_code": None,
            "verification_code_expires_at": None,
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])

        # Call password reset request endpoint
        data = {"email": user["email"]}
        response = client.post(
            f"{settings.API_V1_STR}/user/password_reset/request", params=data
        )

        expected_response = {"message": "Password reset email sent"}
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_response

    @patch("app.api.api_v1.endpoints.user.AWSEmailExecuter")
    @patch("app.api.api_v1.endpoints.user.EmailService")
    def test_password_reset_request_email_not_exists(
        self, mock_email_service, mock_aws_email_executer, request
    ):
        app = request.instance.app
        client = request.instance.client
        user_store = request.instance.user_store

        app.dependency_overrides[deps.get_user_store] = lambda: user_store

        # Call password reset request endpoint
        data = {"email": "gorocoaico@gmail.com"}
        response = client.post(
            f"{settings.API_V1_STR}/user/password_reset/request", params=data
        )

        expected_response = {"detail": "Malformed Data"}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_response

    @patch("app.api.api_v1.endpoints.user.AWSEmailExecuter")
    @patch("app.api.api_v1.endpoints.user.EmailService")
    def test_password_reset_request_email_not_verified(
        self, mock_email_service, mock_aws_email_executer, request
    ):
        app = request.instance.app
        client = request.instance.client
        user_store = request.instance.user_store

        app.dependency_overrides[deps.get_user_store] = lambda: user_store

        # Add user to store
        password_plain_text = request.instance.valid_passwords[0]
        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": False,
            "verification_code": None,
            "verification_code_expires_at": None,
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])

        # Call password reset request endpoint
        data = {"email": user["email"]}
        response = client.post(
            f"{settings.API_V1_STR}/user/password_reset/request", params=data
        )

        expected_response = {"detail": "Malformed Data"}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_response

    def test_password_reset_verify_success(self, request):
        app = request.instance.app
        client = request.instance.client
        user_store = request.instance.user_store
        force_equals = request.instance.force_equals

        app.dependency_overrides[deps.get_user_store] = lambda: user_store

        # Add user to store
        password_plain_text = request.instance.valid_passwords[0]
        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": True,
            "verification_code": None,
            "verification_code_expires_at": None,
            "password_reset_code": "FGD69G",
            "password_reset_code_expires_at": (
                datetime.now() + timedelta(days=10)
            ).replace(tzinfo=timezone.utc),
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])

        # Call password reset verify endpoint
        data = {
            "email": user["email"],
            "password_reset_code": user["password_reset_code"],
            "new_password": request.instance.valid_passwords[1],
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/password_reset/verify",
            data=data,
            headers=headers,
        )

        expected_response = {
            "access_token": force_equals,
            "token_type": "bearer",
        }
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_response

    def test_password_reset_verify_user_not_exists(self, request):
        client = request.instance.client
        user_store = request.instance.user_store

        app = request.instance.app
        app.dependency_overrides[deps.get_user_store] = lambda: user_store

        # Call password reset verify endpoint
        data = {
            "email": "gorocoaico@gmail.com",
            "password_reset_code": "not_a_real_code",
            "new_password": request.instance.valid_passwords[1],
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/password_reset/verify",
            data=data,
            headers=headers,
        )

        expected_response = {"detail": "Malformed Data"}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_response

    def test_password_reset_verify_code_not_match(self, request):
        app = request.instance.app
        client = request.instance.client
        user_store = request.instance.user_store

        app.dependency_overrides[deps.get_user_store] = lambda: user_store

        # Add user to store
        password_plain_text = request.instance.valid_passwords[0]
        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": True,
            "verification_code": None,
            "verification_code_expires_at": None,
            "password_reset_code": "FGD69G",
            "password_reset_code_expires_at": (
                datetime.now() + timedelta(days=10)
            ).replace(tzinfo=timezone.utc),
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])

        # Call password reset verify endpoint
        data = {
            "email": user["email"],
            "password_reset_code": "not_the_correct_code",
            "new_password": request.instance.valid_passwords[1],
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/password_reset/verify",
            data=data,
            headers=headers,
        )

        expected_response = {"detail": "Malformed Data"}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_response

    def test_password_reset_verify_code_expired(self, request):
        app = request.instance.app
        client = request.instance.client
        user_store = request.instance.user_store

        app.dependency_overrides[deps.get_user_store] = lambda: user_store

        # Add user to store
        password_plain_text = request.instance.valid_passwords[0]
        password_reset_code = "FGD69G"
        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico+test_password_reset_verify_code_expired@gmail.com",
            "full_name": None,
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": True,
            "verification_code": None,
            "verification_code_expires_at": None,
            "password_reset_code": password_reset_code,
            "password_reset_code_expires_at": (
                datetime.now() - timedelta(days=10)
            ).replace(tzinfo=timezone.utc),
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])

        # Call password reset verify endpoint
        data = {
            "email": user["email"],
            "password_reset_code": password_reset_code,
            "new_password": request.instance.valid_passwords[1],
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/password_reset/verify",
            data=data,
            headers=headers,
        )

        expected_response = {"detail": "Malformed Data"}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_response

    def test_get_user_by_id_success(self, request):
        """Test successful retrieval of user by ID"""
        app = request.instance.app
        client = request.instance.client
        user_store = request.instance.user_store

        # Set up user store dependency
        app.dependency_overrides[deps.get_user_store] = lambda: user_store

        password_plain_text = request.instance.valid_passwords[0]
        password_reset_code = "FGD69G"
        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico+test_get_user_by_id_success@gmail.com",
            "full_name": None,
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": True,
            "verification_code": None,
            "verification_code_expires_at": None,
            "password_reset_code": password_reset_code,
            "password_reset_code_expires_at": (
                datetime.now() - timedelta(days=10)
            ).replace(tzinfo=timezone.utc),
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])
        
        # Verify user exists in store
        stored_user = user_store.get(user["group"], user["id"])
        assert stored_user is not None, f"User not found in store with ID {user['id']}"
        assert str(stored_user.id) == user["id"], f"Stored user ID {stored_user.id} doesn't match {user['id']}"
        
        # Get user by email to verify email index
        user_data = get_user_by_email(user['email'], user_store)
        assert user_data is not None, f"User not found in store with email {user['email']}"
        assert str(user_data.id) == user["id"], f"User data ID {user_data.id} doesn't match {user['id']}"

        # Mock current user for authentication
        app.dependency_overrides[deps.get_current_user] = lambda: User(**user)

        # Test getting user by ID
        print(f"\nDebug: Attempting to get user with ID {user['id']}")
        print(f"Debug: User store contains: {list(user_store.list())}")
        
        response = client.get(f"{settings.API_V1_STR}/user/users/{user['id']}")
        print(f"Debug: Response status: {response.status_code}")
        print(f"Debug: Response body: {response.json() if response.status_code != 404 else 'Not Found'}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == user["id"]
        assert data["email"] == user["email"]
        assert data["is_verified"] == user["is_verified"]
        assert "password" not in data

    def test_get_user_by_id_not_found(self, request):
        """Test getting a non-existent user by ID"""
        app = request.instance.app
        client = request.instance.client

        # Get the existing test user for authentication
        test_user = User(
            email="gorocoaico@gmail.com",
            password=request.instance.valid_passwords[0],
        )

        # Mock current user for authentication
        app.dependency_overrides[deps.get_current_user] = lambda: test_user

        # Test getting non-existent user
        response = client.get(f"{settings.API_V1_STR}/user/users/{uuid.uuid4()}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Not found"

    def test_get_user_by_email_success(self, request):
        """Test successful retrieval of user by email"""
        app = request.instance.app
        client = request.instance.client
        user_store = request.instance.user_store

        # Set up user store dependency
        app.dependency_overrides[deps.get_user_store] = lambda: user_store

        password_plain_text = request.instance.valid_passwords[0]
        password_reset_code = "FGD69G"
        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico+test_get_user_by_email_success@gmail.com",
            "full_name": None,
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": True,
            "verification_code": None,
            "verification_code_expires_at": None,
            "password_reset_code": password_reset_code,
            "password_reset_code_expires_at": (
                datetime.now() - timedelta(days=10)
            ).replace(tzinfo=timezone.utc),
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])
        user_data = get_user_by_email(user['email'], user_store)
        assert user_data is not None, "Test user not found in store"

        # Mock current user for authentication - use User model instance
        app.dependency_overrides[deps.get_current_user] = lambda: User(**user)

        # Test getting user by email
        response = client.get(f"{settings.API_V1_STR}/user/users/email/{user_data.email}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(user_data.id)
        assert data["email"] == user_data.email
        assert data["is_verified"] == user_data.is_verified
        assert "password" not in data  # Password should not be exposed

    def test_get_user_by_email_not_found(self, request):
        """Test getting a non-existent user by email"""
        app = request.instance.app
        client = request.instance.client

        # Get the existing test user for authentication
        test_user = User(
            email="gorocoaico@gmail.com",
            password=request.instance.valid_passwords[0],
        )

        # Mock current user for authentication
        app.dependency_overrides[deps.get_current_user] = lambda: test_user
        app.dependency_overrides[deps.owner_or_admin_for_user_by_email] = lambda: User(**test_user)

        # Test getting non-existent user
        response = client.get(f"{settings.API_V1_STR}/user/users/email/goricoaico+nonexistent@gmail.com")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Not found"

    def test_get_user_by_email_case_insensitive(self, request):
        """Test that email lookup is case insensitive"""
        app = request.instance.app
        client = request.instance.client
        user_store = request.instance.user_store

        password_plain_text = request.instance.valid_passwords[0]
        password_reset_code = "FGD69G"
        user = {
            "id": str(uuid.uuid4()),
            "email": "gorocoaico+test_get_user_by_email_case_insensitive@gmail.com",
            "full_name": None,
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": True,
            "verification_code": None,
            "verification_code_expires_at": None,
            "password_reset_code": password_reset_code,
            "password_reset_code_expires_at": (
                datetime.now() - timedelta(days=10)
            ).replace(tzinfo=timezone.utc),
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])

        # Set up user store dependency after we have the test user
        app.dependency_overrides[deps.get_current_user] = lambda: User(**user)
        app.dependency_overrides[deps.owner_or_admin_for_user_by_email] = lambda: User(**test_user)

        user_data = get_user_by_email(user['email'], user_store)
        assert user_data is not None, "Test user not found in store"

        # Test with uppercase email
        response = client.get(f"{settings.API_V1_STR}/user/users/email/{user_data.email.upper()}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == user_data.email  # Should return original case
        assert data["id"] == str(user_data.id)
        assert "password" not in data  
        assert "password_reset_code" not in data 

    def test_get_user_by_id_authorization_self_access(self, request):
        """Test that a user can access their own data"""
        app = request.instance.app
        client = request.instance.client
        user_store = request.instance.user_store

        # Create a test user
        user = {
            "id": str(uuid.uuid4()),
            "email": "goricoaico+test_get_user_by_id_authorization_self_access@gmail.com",
            "password": utils.get_password_hash(request.instance.valid_passwords[0]),
            "is_verified": True,
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])

        # Mock current user as the test user
        app.dependency_overrides[deps.get_current_user] = lambda: User(**user)
        app.dependency_overrides[deps.owner_or_admin_for_user] = lambda: User(**user)

        # Try to get own user details
        response = client.get(f"{settings.API_V1_STR}/user/users/{user['id']}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == user["id"]
        assert data["email"] == user["email"]

    def test_get_user_by_id_authorization_other_user_denied(self, request):
        """Test that a user cannot access another user's data"""
        app = request.instance.app
        client = request.instance.client
        user_store = request.instance.user_store

        # Create two test users
        user1 = {
            "id": str(uuid.uuid4()),
            "email": "goricoaico+test_get_user_by_id_authorization_other_user_denied_user1@gmail.com",
            "password": utils.get_password_hash(request.instance.valid_passwords[0]),
            "is_verified": True,
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "group":"test_group"
        }
        user2 = {
            "id": str(uuid.uuid4()),
            "email": "goricoaico+test_get_user_by_id_authorization_other_user_denied_user2@gmail.com",
            "password": utils.get_password_hash(request.instance.valid_passwords[0]),
            "is_verified": True,
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "group":"test_group"
        }
        user_store.create(User(**user1), user1['group'])
        user_store.create(User(**user2), user2['group'])
        

        # Mock current user as user1
        app.dependency_overrides[deps.get_current_user] = lambda: User(**user1)
        # Mock owner_or_admin check to return user1 (not admin)
        app.dependency_overrides[deps.owner_or_admin_for_user] = lambda: User(**user1)

        # Try to get user2's details
        response = client.get(f"{settings.API_V1_STR}/user/users/{user2['id']}")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "Access denied"

    def test_get_user_by_id_authorization_admin_access(self, request):
        """Test that an admin user can access any user's data"""
        app = request.instance.app
        client = request.instance.client
        user_store = request.instance.user_store

        # Create a regular user
        regular_user = {
            "id": str(uuid.uuid4()),
            "email": "goricoaico+test_get_user_by_id_authorization_admin_access_regular@gmail.com",
            "password": utils.get_password_hash(request.instance.valid_passwords[0]),
            "is_verified": True,
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "group":"test_group"
        }
        # Create an admin user
        admin_user = {
            "id": str(uuid.uuid4()),
            "email": "goricoaico+test_get_user_by_id_authorization_admin_access_admin@gmail.com",
            "password": utils.get_password_hash(request.instance.valid_passwords[0]),
            "is_verified": True,
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "role": "admin",  # Add admin role
            "group":"test_group"
        }
        user_store.create(User(**admin_user), admin_user['group'])
        user_store.create(User(**regular_user), regular_user['group'])


        # Mock current user as admin
        app.dependency_overrides[deps.get_current_user] = lambda: User(**admin_user)
        # Mock owner_or_admin check to return admin user
        app.dependency_overrides[deps.owner_or_admin_for_user] = lambda: User(**admin_user)

        # Try to get regular user's details
        response = client.get(f"{settings.API_V1_STR}/user/users/{regular_user['id']}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == regular_user["id"]
        assert data["email"] == regular_user["email"]


class TestUserAdmin:
    """Test cases for admin user management endpoints"""
    
    def test_list_users_success(self, request):
        """Test successful listing of users with pagination"""
        user_store = request.instance.user_store
        client = request.instance.client
        app = request.instance.app
        
        # Create test admin user
        admin_user = User(
            id=uuid.uuid4(),
            email="goricoaico+admin@gmail.com",
            password=utils.get_password_hash("AdminPass123!"),
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="admin",
            group="test_group"
        )
        user_store.create(admin_user, admin_user.group)
        
        # Create test regular users
        test_users = []
        for i in range(3):
            user = User(
                id=uuid.uuid4(),
                email=f"goricoaico+{i}@gmail.com",
                password=utils.get_password_hash(f"UserPass{i}123!"),
                disabled=False,
                created_at=datetime.now(timezone.utc),
                is_verified=True,
                group="test_group"
            )
            user_store.create(user, user.group)

            test_users.append(user)
            
        # Get admin token
        admin_token = create_access_token(data={"sub": admin_user.email})
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test listing users
        response = client.get(f"{settings.API_V1_STR}/user/users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 4  # 3 test users
        
        # Verify user data structure
        user = data[0]
        assert "id" in user
        assert "email" in user
        assert "disabled" in user
        assert "is_verified" in user
        assert "created_at" in user
        assert "password" not in user  # Password should not be exposed
        
        # Test pagination
        response = client.get(f"{settings.API_V1_STR}/user/users?skip=1&limit=2", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_users_unauthorized(self, request):
        """Test listing users without authentication"""
        client = request.instance.client
        
        response = client.get(f"{settings.API_V1_STR}/user/users")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

    def test_list_users_invalid_pagination(self, request):
        """Test listing users with invalid pagination parameters"""
        user_store = request.instance.user_store
        client = request.instance.client
        
        # Create test admin user and get token
        admin_user = User(
            id=uuid.uuid4(),
            email="goricoaico+admin@gmail.com",
            password=utils.get_password_hash("AdminPass123!"),
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group="test_group"
        )
        user_store.create(admin_user, admin_user.group)
        admin_token = create_access_token(data={"sub": admin_user.email})
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test negative skip
        response = client.get(f"{settings.API_V1_STR}/user/users?skip=-1", headers=admin_headers)
        assert response.status_code == 422
        
        # Test zero limit
        response = client.get(f"{settings.API_V1_STR}/user/users?limit=0", headers=admin_headers)
        assert response.status_code == 422
        
        # Test limit too large
        response = client.get(f"{settings.API_V1_STR}/user/users?limit=101", headers=admin_headers)
        assert response.status_code == 422

    def test_create_user_success(self, request):
        """Test successful user creation by admin"""
        user_store = request.instance.user_store
        client = request.instance.client
        
        # Setup admin user and get token
        admin_user = User(
            id=uuid.uuid4(),
            email="goricoaico+admin@gmail.com",
            password=utils.get_password_hash("AdminPass123!"),
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="admin",
            group="test_group"
        )
        user_store.create(admin_user, admin_user.group)
        admin_token = create_access_token(data={"sub": admin_user.email})
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test creating new user
        new_user_data = {
            "email": "goricoaico+newuser@gmail.com",
            "password": "NewUserPass123!"
        }
        response = client.post(f"{settings.API_V1_STR}/user/users", json=new_user_data, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert data["email"] == new_user_data["email"]
        assert data["is_verified"] is True  # Admin-created users are pre-verified
        assert "password" not in data
        
        # Verify user was actually created
        user = get_user_by_email(new_user_data["email"], user_store)
        assert user is not None
        assert user.email == new_user_data["email"]
        assert user.is_verified is True

    def test_create_user_duplicate_email(self, request):
        """Test creating user with existing email"""
        user_store = request.instance.user_store
        client = request.instance.client
        
        # Setup admin user and get token
        admin_user = User(
            id=uuid.uuid4(),
            email="goricoaico+admin@gmail.com",
            password=utils.get_password_hash("AdminPass123!"),
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group="test_group"
        )
        user_store.create(admin_user, admin_user.group)
        admin_token = create_access_token(data={"sub": admin_user.email})
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create a test user first
        test_user = User(
            id=uuid.uuid4(),
            email="goricoaico+existing@gmail.com",
            password=utils.get_password_hash("TestPass123!"),
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group="test_group"
        )
        user_store.create(test_user, test_user.group)
        
        # Try to create user with same email
        new_user_data = {
            "email": test_user.email,  # Use existing email
            "password": "NewUserPass123!"
        }
        response = client.post(f"{settings.API_V1_STR}/user/users", json=new_user_data, headers=admin_headers)
        assert response.status_code == 400
        assert "User already exists" in response.json()["detail"]

    def test_create_user_invalid_data(self, request):
        """Test creating user with invalid data"""
        user_store = request.instance.user_store
        client = request.instance.client
        
        # Setup admin user and get token
        admin_user = User(
            id=uuid.uuid4(),
            email="goricoaico+admin@gmail.com",
            password=utils.get_password_hash("AdminPass123!"),
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group="test_group"
        )
        user_store.create(admin_user, admin_user.group)
        admin_token = create_access_token(data={"sub": admin_user.email})
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test missing required fields
        response = client.post(f"{settings.API_V1_STR}/user/users", json={}, headers=admin_headers)
        assert response.status_code == 422
        
        # Test invalid email format
        response = client.post(
            f"{settings.API_V1_STR}/user/users",
            json={"email": "invalid-email", "password": "ValidPass123!"},
            headers=admin_headers
        )
        assert response.status_code == 422
        
        # Test invalid password format
        response = client.post(
            f"{settings.API_V1_STR}/user/users",
            json={"email": "goricoaico+valid@gmail.com", "password": "weak"},
            headers=admin_headers
        )
        assert response.status_code == 422

    def test_create_user_unauthorized(self, request):
        """Test creating user without authentication"""
        client = request.instance.client
        
        new_user_data = {
            "email": "goricoaico+newuser@gmail.com",
            "password": "NewUserPass123!"
        }
        response = client.post(f"{settings.API_V1_STR}/user/users", json=new_user_data)
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

    def test_update_user_success(self, request):
        """Test successful user update by admin"""
        client = request.instance.client
        user_store = request.instance.user_store
        force_equals = request.instance.force_equals

        # Setup dependencies
        request.instance.app.dependency_overrides[deps.get_user_store] = lambda: user_store
        
        # Create test user
        user_id = uuid.uuid4()
        password_plain_text = request.instance.valid_passwords[0]
        user = {
            "id": str(user_id),
            "email": "gorocoaico+test_update_user_success@gmail.com",
            "full_name": "Original Name",
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "last_login": None,
            "is_verified": True,
            "verification_code": None,
            "verification_code_expires_at": None,
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])

        # Create admin user and get token
        admin_user = {
            "id": str(uuid.uuid4()),
            "email": "goricoaico+test_update_user_success_admin@gmail.com",
            "full_name": "Admin User",
            "password": utils.get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "last_login": None,
            "is_verified": True,
            "role": "admin",
            "group":"test_group"
        }
        user_store.create(User(**admin_user), admin_user['group'])  
        
        # Get admin token
        admin_token = create_access_token(data={"sub": admin_user["email"]})
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Update data
        update_data = {
            "full_name": "Updated Name",
            "disabled": True
        }

        # Make request
        response = client.put(
            f"{settings.API_V1_STR}/user/users/{user_id}",
            json=update_data,
            headers=headers
        )

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["id"] == str(user_id)
        assert response_data["email"] == user["email"]
        assert response_data["full_name"] == "Updated Name"
        assert response_data["disabled"] is False
        assert response_data["is_verified"] is True

    def test_update_user_not_found(self, request):
        """Test updating non-existent user"""
        client = request.instance.client
        user_store = request.instance.user_store

        # Setup dependencies
        request.instance.app.dependency_overrides[deps.get_user_store] = lambda: user_store

        # Create admin user and get token
        admin_user = {
            "id": str(uuid.uuid4()),
            "email": "goricoaico+test_update_user_not_found_admin@gmail.com",
            "full_name": "Admin User",
            "password": utils.get_password_hash(request.instance.valid_passwords[0]),
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "last_login": None,
            "is_verified": True,
            "role": "admin",
            "group":"test_group"
        }
        user_store.create(User(**admin_user), admin_user['group'])
        
        # Get admin token
        admin_token = create_access_token(data={"sub": admin_user["email"]})
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Try to update non-existent user
        non_existent_id = uuid.uuid4()
        update_data = {"full_name": "New Name"}

        response = client.put(
            f"{settings.API_V1_STR}/user/users/{non_existent_id}",
            json=update_data,
            headers=headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "Not found"}

    def test_update_user_unauthorized(self, request):
        """Test updating user without authentication"""
        client = request.instance.client
        user_store = request.instance.user_store

        # Setup dependencies
        request.instance.app.dependency_overrides[deps.get_user_store] = lambda: user_store

        # Create test user
        user_id = uuid.uuid4()
        user = {
            "id": str(user_id),
            "email": "gorocoaico+test_update_user_unauthorized@gmail.com",
            "full_name": "Test User",
            "password": utils.get_password_hash(request.instance.valid_passwords[0]),
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "last_login": None,
            "is_verified": True,
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])

        # Try to update without auth token
        update_data = {"full_name": "New Name"}
        response = client.put(
            f"{settings.API_V1_STR}/user/users/{user_id}",
            json=update_data
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == {"detail": "Not authenticated"}

    def test_update_user_password(self, request):
        """Test updating user password"""
        client = request.instance.client
        user_store = request.instance.user_store

        # Setup dependencies
        request.instance.app.dependency_overrides[deps.get_user_store] = lambda: user_store

        # Create test user
        user_id = uuid.uuid4()
        old_password = request.instance.valid_passwords[0]
        user = {
            "id": str(user_id),
            "email": "gorocoaico+test_update_user_password@gmail.com",
            "full_name": "Test User",
            "password": utils.get_password_hash(old_password),
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "last_login": None,
            "is_verified": True,
            "role": "admin",
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])
        request.instance.app.dependency_overrides[deps.owner_or_admin_for_user] = lambda: User(**user)

        # Get admin token
        admin_token = create_access_token(data={"sub": user["email"]})
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Update password
        new_password = request.instance.valid_passwords[1]
        update_data = {"password": new_password}

        response = client.put(
            f"{settings.API_V1_STR}/user/users/{user_id}",
            json=update_data,
            headers=headers
        )

        assert response.status_code == status.HTTP_200_OK
        
        # Verify password was updated by trying to login with new password
        login_data = {
            "username": user["email"],
            "password": new_password
        }
        login_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        login_response = client.post(
            f"{settings.API_V1_STR}/user/login",
            data=login_data,
            headers=login_headers
        )
        assert login_response.status_code == status.HTTP_200_OK

    def test_update_user_self_access(self, request):
        """Test user updating their own profile"""
        client = request.instance.client
        user_store = request.instance.user_store

        # Setup dependencies
        request.instance.app.dependency_overrides[deps.get_user_store] = lambda: user_store

        # Create test user
        user_id = uuid.uuid4()
        password = request.instance.valid_passwords[0]
        user = {
            "id": str(user_id),
            "email": "gorocoaico+test_update_user_self@gmail.com",
            "full_name": "Original Name",
            "password": utils.get_password_hash(password),
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "last_login": None,
            "is_verified": True,
            "group":"test_group"
        }
        user_store.create(User(**user), user['group'])

        # Get user token
        user_token = create_access_token(data={"sub": user["email"]})
        headers = {"Authorization": f"Bearer {user_token}"}

        # Update own profile
        update_data = {
            "full_name": "Updated Self Name",
            "disabled": False  # Should not be able to change this
        }

        response = client.put(
            f"{settings.API_V1_STR}/user/users/{user_id}",
            json=update_data,
            headers=headers
        )

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["id"] == str(user_id)
        assert response_data["email"] == user["email"]
        assert response_data["full_name"] == "Updated Self Name"
        assert response_data["disabled"] is False  # Should remain unchanged

    def test_list_users_regular_user_forbidden(self, request):
        """Test that regular users cannot access the list users endpoint"""
        user_store = request.instance.user_store
        client = request.instance.client
        
        # Create a regular user (non-admin)
        regular_user = User(
            id=uuid.uuid4(),
            email="goricoaico+regular@gmail.com",
            password=utils.get_password_hash("UserPass123!"),
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group="test_group"
        )
        user_store.create(regular_user, regular_user.group)
        
        # Get regular user token
        user_token = create_access_token(data={"sub": regular_user.email})
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Try to list users as regular user - should be forbidden
        response = client.get(f"{settings.API_V1_STR}/user/users", headers=user_headers)
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"

    def test_create_user_regular_user_forbidden(self, request):
        """Test that regular users cannot create other users"""
        user_store = request.instance.user_store
        client = request.instance.client
        
        # Create a regular user (non-admin)
        regular_user = User(
            id=uuid.uuid4(),
            email="goricoaico+regular@gmail.com",
            password=utils.get_password_hash("UserPass123!"),
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group="test_group"
        )
        user_store.create(regular_user, regular_user.group)
        
        # Get regular user token
        user_token = create_access_token(data={"sub": regular_user.email})
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Try to create a new user as regular user - should be forbidden
        new_user_data = {
            "email": "goricoaico+newuser@gmail.com",
            "password": "NewUserPass123!"
        }
        response = client.post(f"{settings.API_V1_STR}/user/users", json=new_user_data, headers=user_headers)
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"

    def test_update_other_user_regular_user_forbidden(self, request):
        """Test that regular users cannot update other users' data"""
        user_store = request.instance.user_store
        client = request.instance.client
        
        # Create two regular users
        user1 = User(
            id=uuid.uuid4(),
            email="goricoaico+user1@gmail.com",
            password=utils.get_password_hash("UserPass123!"),
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group="test_group"
        )
        user2 = User(
            id=uuid.uuid4(),
            email="goricoaico+user2@gmail.com",
            password=utils.get_password_hash("UserPass123!"),
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group="test_group"
        )
        user_store.create(user1, user1.group)
        user_store.create(user2, user2.group)
        
        # Get user1 token
        user1_token = create_access_token(data={"sub": user1.email})
        user1_headers = {"Authorization": f"Bearer {user1_token}"}
        
        # Try to update user2's data as user1 - should be forbidden
        update_data = {
            "full_name": "Updated by User1",
            "disabled": True
        }
        response = client.put(
            f"{settings.API_V1_STR}/user/users/{user2.id}",
            json=update_data,
            headers=user1_headers
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"

    def test_update_user_put_endpoint_admin_or_self_only(self, request):
        """Test that PUT /users/{user_id} only allows admin or self to update records"""
        user_store = request.instance.user_store
        client = request.instance.client
        
        # Create three users: admin, user1, and user2
        admin_user = User(
            id=uuid.uuid4(),
            email="goricoaico+admin@gmail.com",
            password=utils.get_password_hash("AdminPass123!"),
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="admin",
            group="test_group"
        )
        
        user1 = User(
            id=uuid.uuid4(),
            email="goricoaico+user1@gmail.com",
            password=utils.get_password_hash("UserPass123!"),
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group="test_group"
        )
        
        user2 = User(
            id=uuid.uuid4(),
            email="goricoaico+user2@gmail.com",
            password=utils.get_password_hash("UserPass123!"),
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group="test_group"
        )
        
        user_store.create(admin_user, admin_user.group)
        user_store.create(user1, user1.group)
        user_store.create(user2, user2.group)
        
        # Test 1: Admin can update any user (should succeed)
        admin_token = create_access_token(data={"sub": admin_user.email})
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        update_data = {"full_name": "Updated by Admin"}
        response = client.put(
            f"{settings.API_V1_STR}/user/users/{user1.id}",
            json=update_data,
            headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Updated by Admin"
        
        # Test 2: User can update themselves (should succeed)
        user1_token = create_access_token(data={"sub": user1.email})
        user1_headers = {"Authorization": f"Bearer {user1_token}"}
        
        update_data = {"full_name": "Updated by Self"}
        response = client.put(
            f"{settings.API_V1_STR}/user/users/{user1.id}",
            json=update_data,
            headers=user1_headers
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Updated by Self"
        
        # Test 3: User cannot update another user (should fail)
        user1_token = create_access_token(data={"sub": user1.email})
        user1_headers = {"Authorization": f"Bearer {user1_token}"}
        
        update_data = {"full_name": "Updated by User1"}
        response = client.put(
            f"{settings.API_V1_STR}/user/users/{user2.id}",
            json=update_data,
            headers=user1_headers
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"
        
        # Test 4: User2 cannot update user1 (should fail)
        user2_token = create_access_token(data={"sub": user2.email})
        user2_headers = {"Authorization": f"Bearer {user2_token}"}
        
        update_data = {"full_name": "Updated by User2"}
        response = client.put(
            f"{settings.API_V1_STR}/user/users/{user1.id}",
            json=update_data,
            headers=user2_headers
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"
        
        # Test 5: Admin can update themselves (should succeed)
        admin_token = create_access_token(data={"sub": admin_user.email})
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        update_data = {"full_name": "Admin Updated Self"}
        response = client.put(
            f"{settings.API_V1_STR}/user/users/{admin_user.id}",
            json=update_data,
            headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Admin Updated Self"

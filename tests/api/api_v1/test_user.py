from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import status

from app.api import deps
from app.api.utils import get_password_hash
from app.core.config import settings
from app.schemas import User


class TestUser:
    @patch("app.api.api_v1.endpoints.user.send_verification_email")
    def test_signup_success(self, mock_send_verification_email, request):
        client = request.instance.client
        force_equals = request.instance.force_equals
        user_store = request.instance.user_store

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )

        data = {
            "email": "gorocoaico@gmail.com",
            "password": request.instance.valid_passwords[0],
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/signup", data=data, headers=headers
        )

        expected_response = {
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": force_equals,
            "disabled": False,
            "created_at": force_equals,
            "last_login": None,
            "is_verified": False,
            "verification_code": None,
            "verification_code_expires_at": None,
            "password_reset_code": None,
            "password_reset_code_expires_at": None,
        }

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_response

    def test_signup_user_already_exists(self, request):
        user_store = request.instance.user_store
        client = request.instance.client

        request.instance.app.dependency_overrides[deps.get_user_store] = (
            lambda: user_store
        )

        password_plain_text = request.instance.valid_passwords[0]
        user = {
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": False,
            "verification_code": "FGD69G",
            "verification_code_expires_at": (
                datetime.now() + timedelta(days=10)
            ).replace(tzinfo=timezone.utc),
        }
        user_store.put(user["email"], user)

        data = {"email": user["email"], "password": password_plain_text}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/signup", data=data, headers=headers
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
            "email": "gorocoaico@gmail.com",
            "password": request.instance.valid_passwords[0],
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/signup", data=data, headers=headers
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

        data = {"email": "gorocoaico@gmail.com"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(
            f"{settings.API_V1_STR}/user/signup", data=data, headers=headers
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
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": True,
            "verification_code": None,
            "verification_code_expires_at": None,
        }
        user_store.put(user["email"], user)

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
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": False,
            "verification_code": "FGD69G",
            "verification_code_expires_at": (
                datetime.now() + timedelta(days=10)
            ).replace(tzinfo=timezone.utc),
        }
        user_store.put(user["email"], user)

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
        }
        user_store.put(user["email"], user)

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
        }
        user_store.put(user["email"], user)

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
        }
        user_store.put(user["email"], user)

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
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": request.instance.valid_passwords[0],
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": True,
            "verification_code": None,
            "verification_code_expires_at": None,
        }
        user_store.put(user["email"], user)

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
        }
        user_store.put(user["email"], user)

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

    def test_me_success(self, request):
        app = request.instance.app
        client = request.instance.client

        app.dependency_overrides[deps.get_current_user] = lambda: User(
            email="gorocoaico@gmail.com",
            password=request.instance.valid_passwords[0],
        )

        response = client.get(f"{settings.API_V1_STR}/user/me")

        expected_response = {
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": request.instance.valid_passwords[0],
            "disabled": None,
            "created_at": None,
            "last_login": None,
            "is_verified": None,
            "verification_code": None,
            "verification_code_expires_at": None,
            "password_reset_code": None,
            "password_reset_code_expires_at": None,
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

        app.dependency_overrides[deps.get_current_user] = lambda: User(
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
        app = request.instance.app
        client = request.instance.client
        user_store = request.instance.user_store

        app.dependency_overrides[deps.get_user_store] = lambda: user_store

        # Add user to store
        password_plain_text = request.instance.valid_passwords[0]
        user = {
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": True,
            "verification_code": None,
            "verification_code_expires_at": None,
        }
        user_store.put(user["email"], user)

        # Mock current user so we are authenticated
        app.dependency_overrides[deps.get_current_user] = lambda: User(
            email=user["email"], password=user["password"]
        )

        # Update profile
        data = {"full_name": "John Doe"}
        response = client.post("/api/v1.0/user/update_profile", params=data)

        expected_response = {"message": "Profile updated"}
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_response

    def test_update_profile_unauthenticated(self, request):
        client = request.instance.client

        data = {"full_name": "John Doe"}
        response = client.post("/api/v1.0/user/update_profile", params=data)

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
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": True,
            "verification_code": None,
            "verification_code_expires_at": None,
        }
        user_store.put(user["email"], user)

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
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": get_password_hash(password_plain_text),
            "disabled": False,
            "created_at": None,
            "last_login": None,
            "is_verified": False,
            "verification_code": None,
            "verification_code_expires_at": None,
        }
        user_store.put(user["email"], user)

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
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": get_password_hash(password_plain_text),
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
        }
        user_store.put(user["email"], user)

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
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": get_password_hash(password_plain_text),
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
        }
        user_store.put(user["email"], user)

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
            "email": "gorocoaico@gmail.com",
            "full_name": None,
            "password": get_password_hash(password_plain_text),
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
        }
        user_store.put(user["email"], user)

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

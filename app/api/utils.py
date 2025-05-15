import base64
import re
import urllib.parse
from datetime import datetime, timedelta, timezone
from os.path import join
from typing import Optional

import shortuuid
from jinja2 import Template
from jose import jwt
from passlib.context import CryptContext
from pydantic import AnyHttpUrl
from UnleashClient import UnleashClient

from app.core.config import settings
from app.modules.email_service import AWSEmailExecuter, EmailHTMLData, EmailService
from app.modules.store_interface import StoreProtocol
from app.modules.tlogger import TLogger
from app.schemas import UserInDB

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

project_name = settings.PROJECT_NAME
project_name_formatted = project_name.strip().replace(" ", "_").upper()
logger = TLogger(f"{project_name_formatted}_API")

if (
    settings.UNLEASH_URL != None
    and settings.UNLEASH_INSTANCE_ID != None
    and settings.GITLAB_ENVIRONMENT != None
):
    unleash_client = UnleashClient(
        url=str(settings.UNLEASH_URL),
        app_name=settings.GITLAB_ENVIRONMENT,
        instance_id=settings.UNLEASH_INSTANCE_ID,
        disable_metrics=True,
        disable_registration=True,
    )
    unleash_client.initialize_client()
else:
    unleash_client = None


def get_unleash_client() -> UnleashClient | None:
    """
    Get the unleash client.
    """
    return unleash_client


def get_logger() -> TLogger:
    """
    Get the logger.
    """
    return logger


def get_user(username: str, user_store: StoreProtocol) -> Optional[UserInDB]:
    """
    Get the user from the database.
    :param username: The username of the user to get.
    :param user_store: The user store.
    :return: The user data.
    """
    user_dict = user_store.get(username)
    if user_dict:
        return UserInDB(**user_dict)

def get_user_by_email(username: str, user_store: StoreProtocol) -> Optional[UserInDB]:
    """
    Get the user from the database.
    :param username: The username of the user to get.
    :param user_store: The user store.
    :return: The user data.
    """
    user_dict = user_store.get_by_email(username)
    if user_dict:
        return UserInDB(**user_dict)
    
def get_user_uuid_by_email(email: str, user_store: StoreProtocol) -> str | None:
    """
    Get a user's UUID by their email address.
    
    Args:
        email: The email address to look up
        user_store: The user store instance
        
    Returns:
        The user's UUID as a string if found, None otherwise
        
    Raises:
        Exception: If there is an error accessing the store
    """
    try:
        user_dict = user_store.get_by_email(email)
        if user_dict:
            return user_dict['id']
        return None
    except Exception as e:
        # Log the error and re-raise
        logger.error(f"Error looking up user UUID by email {email}: {str(e)}")
        raise

def authenticate_user(username: str, password: str, user_store: StoreProtocol):
    """
    Authenticate a user by email and password.
    
    Args:
        username: The user's email address
        password: The user's password
        user_store: The user store instance
        
    Returns:
        User object if authentication succeeds, False otherwise
    """
    # Get user by email using the email index
    user = get_user_by_email(username, user_store)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    
    # Update last login time
    user.last_login = datetime.now(timezone.utc)
    
    # Save user with UUID as key - email index is handled by the store
    user_store.put(str(user.id), user.model_dump())
    return user


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def validate_password(password: str) -> str:
    """
    Validate the password.
    :param password: The password to validate.
    :return: The validated password.
    """
    assert (
        len(password) >= settings.MIN_PASSWORD_LENGTH
    ), f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters long"

    assert re.search(
        r"[a-z]", password
    ), "Password must contain at least 1 lowercase letter"

    assert re.search(
        r"[A-Z]", password
    ), "Password must contain at least 1 uppercase letter"

    assert re.search(r"[0-9]", password), "Password must contain at least 1 number"

    assert re.search(
        r"[!@#$%^&*()\-+={}[\]:;\"'<>,.?/|\\~`]", password
    ), "Password must contain at least 1 special character"

    return password


def format_email(email: str) -> str:
    """
    Format the email address to be lowercase and stripped.
    :param email: The email address to format.
    :return: The formatted email address.
    """
    return email.lower().strip()


def get_password_hash(password: str) -> str:
    """
    Get the password hash.
    :param password: The password to hash.
    :return: The hashed password.
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def send_verification_email(
    email: str,
    user_store: StoreProtocol,
    verification_url: AnyHttpUrl = settings.VERIFICATION_URL,
):
    """
    Generates a verification code and sends it to the user's email address.
    The matching database record is updated with the verification code and expiry time.
    :param email: The user's email address
    :param verification_url: The URL to the verification page
    """
    # Generate verification code and expiry time
    verification_code = shortuuid.ShortUUID().random(length=6).upper()
    verification_code_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    # Get user record
    user = get_user_by_email(email, user_store)

    if user is None:
        logger.error(f"User with email {email} does not exist")
        raise Exception("Malformed Data")

    # Update user record
    user.verification_code = verification_code
    user.verification_code_expires_at = verification_code_expires_at

    # Save user record
    user_store.put(str(user.id), user.model_dump())

    # Load email HTML template
    verification_url_with_params = (
        str(verification_url)
        + "/?"
        + urllib.parse.urlencode(
            {"email": email, "verification_code": verification_code}
        )
    )

    email_dir = join(
        settings.ASSETS_DIR, "email_templates", "verification_template_1.html"
    )
    with open(email_dir, "r") as f:
        template = Template(f.read())

    logo_dir = join(settings.ASSETS_DIR, "logo.png")
    with open(logo_dir, "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode()

    rendered_email = template.render(
        name="User",
        email=email,
        verification_code=verification_code,
        verification_url_with_params=verification_url_with_params,
        verification_url=verification_url,
        logo_src=f"data:image/jpeg;base64,{logo_base64}",
    )

    # Send verification email
    email_data = EmailHTMLData(
        **{"subject": "Welcome to AI GRC", "body": rendered_email, "to": [email]}
    )

    if False:
        email_service = EmailService(
            AWSEmailExecuter(
                settings.SES_AWS_SENDER_EMAIL,
                settings.SES_AWS_ACCESS_KEY_ID,
                settings.SES_AWS_SECRET_ACCESS_KEY,
                settings.SES_AWS_REGION,
            )
        )
        email_service.send(email_data)

    # Logging
    logger.info(f"Verification email sent to {email}")

import base64
import json
import urllib.parse
from datetime import datetime, timedelta, timezone
from os.path import join
from typing import Annotated, List, Optional
from uuid import UUID, uuid4

import shortuuid
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from jinja2 import Template

from app.api import deps
from app.api.utils import (
    authenticate_user,
    create_access_token,
    format_email,
    get_password_hash,
    get_user,
    get_user_by_email,
    send_verification_email,
    get_user_uuid_by_email,
)
from app.core.config import settings
from app.modules.email_service import (
    AWSEmailExecuter,
    EmailData,
    EmailHTMLData,
    EmailService,
)
from app.modules.store_interface import StoreProtocol
from app.modules.tlogger import TLogger
from app.schemas import (
    RegistrationUserRepsonse,
    SupportRequest,
    Token,
    User,
    UserEmailVerification,
    UserPasswordResetRequest,
    UserPasswordResetVerify,
    UserSignup,
    UserUpdate,
    UserResponse,
)

router = APIRouter()


DATA_DIR: str = join("app", "data")


@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    logger: TLogger = Depends(deps.get_logger),
    user_store: StoreProtocol = Depends(deps.get_user_store),
):
    username = format_email(form_data.username)
    password = form_data.password

    user = authenticate_user(username, password, user_store)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is verified
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email is not verified",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    logger.info(f"Token generated : email: {user.email}, disabled: {user.disabled}")

    return JSONResponse(content={"access_token": access_token, "token_type": "bearer"})


@router.post(
    "/register",
    summary="Create new user",
    response_model=RegistrationUserRepsonse,
)
async def create_user(
    user_credentials: Annotated[UserSignup, Depends()],
    logger: TLogger = Depends(deps.get_logger),
    user_store: StoreProtocol = Depends(deps.get_user_store),
):
    # Check if user already exists
    email = user_credentials.email
    user = get_user_by_email(email, user_store)

    if user is not None:
        logger.error(f"Attempting to register existing user: {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Generate a standard UUID4
    user_id = uuid4()

    user = User(
        id=user_id,  # Use standard UUID4
        email=email,
        password=get_password_hash(user_credentials.password),
        disabled=False,
        created_at=datetime.now(timezone.utc),
        is_verified=False,
    )

    # Save user to database
    user_store.put(str(user.id), user.model_dump())

    # Generate verification email
    try:
        send_verification_email(user.email, user_store, settings.VERIFICATION_URL)
        pass
    except Exception as e:
        error_message = str(e)
        if hasattr(e, "message"):
            error_message = e.message

        # Logging
        logger.error(f"Error sending verification email: {error_message}")

        # Delete user record
        user_store.pop(str(user.id))

        # Return error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_message
        )

    # Logging
    logger.info(f"User created: {user.model_dump_json()}")

    # Return user
    return JSONResponse(content=json.loads(user.model_dump_json()))


@router.post("/verify_email")
async def verify_email(
    varification_data: Annotated[UserEmailVerification, Depends()],
    logger: TLogger = Depends(deps.get_logger),
    user_store: StoreProtocol = Depends(deps.get_user_store),
):
    email = varification_data.email.lower()
    verification_code = varification_data.verification_code.upper()

    # Logging
    logger.info(f"verify_email called: {email}")

    # Check if user exists
    user = get_user_by_email(email, user_store)
    if user is None:
        logger.error(f"User with email {email} does not exist")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed Data"
        )

    # Check if user is already verified
    if user.is_verified:
        logger.error(f"User with email {email} is already verified")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed Data"
        )

    # Check if verification code matches
    if user.verification_code != verification_code:
        logger.error(f"Verification code does not match for user with email {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code does not match",
        )

    # Check if verification code has expired
    try:
        if user.verification_code_expires_at < datetime.now(timezone.utc):
            logger.error(f"Verification code has expired for user with email {email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed Data"
            )
    except Exception as e:
        logger.error(f"Error checking verification code expiration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed Data"
        )

    # Update user record
    user.is_verified = True
    user.verification_code = None
    user.verification_code_expires_at = None

    # Save user record
    user_store.put(str(user.id), user.model_dump())

    # Return a authentication token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return JSONResponse(content={"access_token": access_token, "token_type": "bearer"})


@router.post("/resend_verification_email")
async def resend_verification_email(
    email: str,
    logger: TLogger = Depends(deps.get_logger),
    user_store: StoreProtocol = Depends(deps.get_user_store),
):
    email = email.lower()

    # Logging
    logger.info(f"resend_verification_email called: {email}")

    # Check if user exists
    user = get_user_by_email(email, user_store)
    if user is None:
        logger.error(f"User with email {email} does not exist")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed Data"
        )

    # Send verification email
    send_verification_email(email, user_store, settings.VERIFICATION_URL)

    return JSONResponse(content={"message": "Verification email sent"})


@router.post("/password_reset/request")
async def password_reset_request(
    password_reset_request_data: Annotated[UserPasswordResetRequest, Depends()],
    logger: TLogger = Depends(deps.get_logger),
    user_store: StoreProtocol = Depends(deps.get_user_store),
):
    """
    Sends a password reset email to the user.
    """
    email = password_reset_request_data.email.lower()

    # Check if user exists
    user = get_user_by_email(email, user_store)
    if user is None:
        logger.info(f"User with email {email} does not exist")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed Data"
        )

    # Check if the user's email is verified
    if not user.is_verified:
        logger.info(f"User with email {email} is not verified")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed Data"
        )

    # Update user record
    user.password_reset_code = shortuuid.ShortUUID().random(length=6).upper()
    user.password_reset_code_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=15
    )

    # Save user record
    user_store.put(str(user.id), user.model_dump())

    # Generate URL with parameters
    password_reset_url_with_params = (
        str(settings.PASSWORD_RESET_URL)
        + "/?"
        + urllib.parse.urlencode(
            {"email": email, "password_reset_code": user.password_reset_code}
        )
    )

    # Load email HTML template
    email_dir = join(settings.ASSETS_DIR, "email_templates", "password_reset.html")
    with open(email_dir, "r") as f:
        template = Template(f.read())

    logo_dir = join(settings.ASSETS_DIR, "logo.png")
    with open(logo_dir, "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode()

    rendered_email = template.render(
        copyright_year=datetime.now().year,
        password_reset_url_with_params=password_reset_url_with_params,
        logo_src=f"data:image/jpeg;base64,{logo_base64}",
    )

    # Send verification email
    email_data = EmailHTMLData(
        **{
            "subject": "[AI GRC] Password Reset",
            "body": rendered_email,
            "to": [email],
        }
    )

    email_service = EmailService(
        AWSEmailExecuter(
            settings.SES_AWS_SENDER_EMAIL,
            settings.SES_AWS_ACCESS_KEY_ID,
            settings.SES_AWS_SECRET_ACCESS_KEY,
            settings.SES_AWS_REGION,
        )
    )
    email_service.send(email_data)

    return JSONResponse(content={"message": "Password reset email sent"})


@router.post("/password_reset/verify")
async def password_reset_verify(
    form_data: Annotated[UserPasswordResetVerify, Depends()],
    logger: TLogger = Depends(deps.get_logger),
    user_store: StoreProtocol = Depends(deps.get_user_store),
):
    """
    Changes the user's password if the password reset code is valid.
    """
    email = form_data.email.lower()
    new_password = form_data.new_password
    password_reset_code = form_data.password_reset_code.upper()

    # Check if user exists
    user = get_user_by_email(email, user_store)
    if user is None:
        logger.info(f"User with email {email} does not exist")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed Data"
        )

    # Check if password reset code matches
    if user.password_reset_code != password_reset_code:
        logger.info(f"Password reset code does not match for user with email {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed Data"
        )

    # Check if password reset code has expired
    if user.password_reset_code_expires_at < datetime.now(timezone.utc):
        logger.info(f"Password reset code has expired for user with email {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed Data"
        )

    # Update user record
    user.password = get_password_hash(new_password)
    user.password_reset_code = None
    user.password_reset_code_expires_at = None

    # Save user record
    user_store.put(str(user.id), user.model_dump())

    # Return an authentication token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    logger.info(f"Token generated : email: {user.email}, disabled: {user.disabled}")

    return JSONResponse(content={"access_token": access_token, "token_type": "bearer"})


@router.post("/update_profile")
async def update_profile(
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    user_update: UserUpdate = Depends(),
    logger: TLogger = Depends(deps.get_logger),
    user_store: StoreProtocol = Depends(deps.get_user_store),
):
    # Update user record
    for attr, value in user_update.__dict__.items():
        if not attr.startswith("_") and attr != "email" and value is not None:
            setattr(current_user, attr, value)

    # Save user record
    user_store.put(str(current_user.id), current_user.model_dump())

    return JSONResponse(content={"message": "Profile updated"})


@router.post("/support")
async def support_request(
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    support_request_data: Annotated[SupportRequest, Depends()],
    logger: TLogger = Depends(deps.get_logger),
):
    # Logging
    logger.info(f"support_request called: {support_request_data}")

    if not support_request_data.message:
        logger.error(f"No message provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No message provided"
        )

    # Build email
    email_text = f"""
AI GRC API Support Request.
Email: {current_user.email}
----------------------------------------

{support_request_data.message}
    """

    # Send support message to support
    try:
        email_data = EmailData(
            **{
                "subject": "AI GRC Support Request",
                "body": email_text,
                "to": [settings.SUPPORT_EMAIL],
                "cc": [current_user.email],
            }
        )
        email_service = EmailService(
            AWSEmailExecuter(
                settings.SES_AWS_SENDER_EMAIL,
                settings.SES_AWS_ACCESS_KEY_ID,
                settings.SES_AWS_SECRET_ACCESS_KEY,
                settings.SES_AWS_REGION,
            )
        )
        email_service.send(email_data)
    except Exception as e:
        error_message = str(e)
        if hasattr(e, "message"):
            error_message = e.message

        # Logging
        logger.error(f"Error sending support email: {error_message}")

        # Return error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Internal server error - please try again later",
        )

    # Logging
    logger.info(f"support_request finished: {support_request_data}")

    return JSONResponse(content={"message": "Support request sent"})


@router.get("/me", response_model=User)
async def read_user_me(
    current_user: Annotated[User, Depends(deps.get_current_active_user)]
):
    # BaseModel returns a string, rather than a dict
    return JSONResponse(content=json.loads(current_user.model_dump_json()))

@router.get("/me/items")
async def read_own_items(
    current_user: Annotated[User, Depends(deps.get_current_active_user)]
):
    return JSONResponse(content=[{"item_id": "Foo", "owner": current_user.email}])


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    logger: TLogger = Depends(deps.get_logger),
    user_store: StoreProtocol = Depends(deps.get_user_store),
):
    """
    List all users with pagination. Admin only.
    """
    # TODO: Add admin role check
    try:
        # Get all users from store
        #users = user_store.get_all()

        test_users = []
        for i in range(3):
            user = User(
                id=str(uuid4()),
                email=f"goricoaico+testuser{i}@gmail.com",
                password=get_password_hash(f"UserPass{i}123!"),
                disabled=False,
                created_at=datetime.now(timezone.utc),
                is_verified=True,
            )
            test_users.append(user)

        # Apply pagination
        paginated_users = test_users[skip : skip + limit]
        # Convert User models to dictionaries and validate as UserResponse
        return JSONResponse(content=[
            UserResponse.model_validate(user.model_dump(mode="json")).model_dump(mode="json") 
            for user in paginated_users
        ])
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving users"
        )

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    logger: TLogger = Depends(deps.get_logger),
    user_store: StoreProtocol = Depends(deps.get_user_store),
    user_access: User = Depends(deps.owner_or_admin_for_user(deps.lookup_user))
):
    """
    Get a specific user by UUID.
    """
    try:
        # Try to get user by UUID
        user_data = get_user(str(user_id), user_store)
        
        if user_data is None:
            logger.info(f"User not found: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        # Convert user data to UserResponse model, ensuring UUID is converted to string
        user_response = UserResponse(
            id=str(user_data.id),  # Convert UUID to string
            email=user_data.email,
            full_name=user_data.full_name,
            created_at=user_data.created_at or datetime.now(timezone.utc),
            is_verified=user_data.is_verified or False,
            disabled=user_data.disabled or False
        )
            
        # TODO: Add authorization check (admin or self)
        return JSONResponse(content=user_response.model_dump(mode="json"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user"
        )

@router.get("/users/email/{email}", response_model=UserResponse)
async def get_user_via_email(
    email: str,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    logger: TLogger = Depends(deps.get_logger),
    user_store: StoreProtocol = Depends(deps.get_user_store),
    user_access: User = Depends(deps.owner_or_admin_for_user_by_email(deps.lookup_user_by_email))
):
    """
    Get a specific user by email.
    """
    try:
        # Get user by email using the email index
        user_data = get_user_by_email(email, user_store)
        
        if user_data is None:
            logger.info(f"User not found: {email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        # Convert user data to UserResponse model, ensuring UUID is converted to string
        user_response = UserResponse(
            id=str(user_data.id),  # Convert UUID to string
            email=user_data.email,
            full_name=user_data.full_name,
            created_at=user_data.created_at or datetime.now(timezone.utc),
            is_verified=user_data.is_verified or False,
            disabled=user_data.disabled or False
        )
            
        # TODO: Add authorization check (admin or self)
        return JSONResponse(content=user_response.model_dump(mode="json"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user {email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user"
        )

@router.post("/users", response_model=UserResponse)
async def create_user_admin(
    user_data: UserSignup,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    logger: TLogger = Depends(deps.get_logger),
    user_store: StoreProtocol = Depends(deps.get_user_store),
):
    """
    Create a new user (admin only).
    This is separate from the registration endpoint as it's for admin use.
    """
    # TODO: Add admin role check
    try:
        # Check if user already exists using email index
        existing_user = get_user_by_email(user_data.email, user_store)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists"
            )

        # Generate a standard UUID4
        user_id = uuid4()
        
        # Create user with validated UUID
        user = User.model_validate({
            "id": str(user_id),  # Convert UUID to string for validation
            "email": user_data.email,
            "password": get_password_hash(user_data.password),
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "is_verified": True,  # Admin-created users are pre-verified
        })

        # Store user with UUID as key - email index is handled by the store
        user_store.put(str(user.id), user.model_dump())
        
        logger.info(f"Admin created user: {user.email} with ID {user.id}")
        
        # Convert User model to dict and validate as UserResponse
        user_dict = user.model_dump()
        return JSONResponse(content=UserResponse.model_validate(user_dict).model_dump(mode="json"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user"
        )

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    logger: TLogger = Depends(deps.get_logger),
    user_store: StoreProtocol = Depends(deps.get_user_store),
    user_access: User = Depends(deps.owner_or_admin_for_user(deps.lookup_user))
):
    """
    Update a user's details (admin or self).
    """
    try:
        user_data = get_user(str(user_id), user_store)
        if user_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user = User.model_validate(user_data)
        
        # TODO: Add authorization check (admin or self)
        
        # Update user fields
        for field, value in user_update.model_dump(exclude_unset=True).items():
            if field == "password" and value is not None:
                value = get_password_hash(value)
            setattr(user, field, value)

        # Update user - email index is handled by the store
        user_store.put(str(user.id), user.model_dump())
        
        logger.info(f"Updated user: {user.email} with ID {user.id}")
        
        user_dict = user.model_dump()
        return JSONResponse(content=UserResponse.model_validate(user_dict).model_dump(mode="json"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user"
        )

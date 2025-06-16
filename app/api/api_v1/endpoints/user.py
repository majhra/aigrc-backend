import base64
import json
import urllib.parse
from datetime import datetime, timedelta, timezone
from os.path import join
from typing import Annotated, List, Optional
from uuid import UUID, uuid4

import shortuuid
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query, Body
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
    send_invite_email,
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
from app.modules.user_store import UserStore
from app.modules.group_store import GroupStore
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
    GroupResponse,
    UserInvite,
)

router = APIRouter()


DATA_DIR: str = join("app", "data")


@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    logger: TLogger = Depends(deps.get_logger),
    user_store: UserStore = Depends(deps.get_user_store),
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
    user_store: UserStore = Depends(deps.get_user_store),
    group_store: GroupStore = Depends(deps.get_group_store),
):
    # Check if user already exists
    email = user_credentials.email
    logger.info(f"create_user called: {email}")
    user = user_store.get_by_email(email)
    logger.info(f"create_user finished: {email}")

    if user is not None:
        logger.error(f"Attempting to register existing user: {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Create a new group for this user
    from app.schemas import GroupCreate
    group_data = GroupCreate(
        name=f"Group for {email}",
        description=f"Personal group for user {email}"
    )
    new_group = group_store.create(group_data, "system")
    group_id = str(new_group.id)

    # Generate a standard UUID4
    user_id = uuid4()

    user = User(
        id=user_id,  # Use standard UUID4
        email=email,
        password=get_password_hash(user_credentials.password),
        disabled=False,
        created_at=datetime.now(timezone.utc),
        is_verified=False,
        group=group_id,  # This is already a string from str(new_group.id)
    )

    # Save user to database with group structure
    user_store.create(user, group_id)

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

        # Delete user record and group
        user_store.delete(group_id, str(user.id))
        group_store.delete(group_id)

        # Return error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_message
        )

    # Logging
    logger.info(f"User created: {user.model_dump_json()}")

    # Fetch group data for the response
    group_response = None
    if user.group:
        group_data = group_store.get(user.group)
        if group_data:
            group_response = GroupResponse.model_validate(group_data.model_dump())
    
    # Create UserResponse with proper group data, excluding sensitive fields
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        created_at=user.created_at or datetime.now(timezone.utc),
        last_login=user.last_login,
        is_verified=user.is_verified or False,
        disabled=user.disabled or False,
        group=group_response
    )
    
    # Return proper registration response
    registration_response = RegistrationUserRepsonse(
        message="User created successfully. Please check your email for verification.",
        data=user_response
    )
    
    return registration_response


@router.post("/verify_email")
async def verify_email(
    varification_data: Annotated[UserEmailVerification, Depends()],
    logger: TLogger = Depends(deps.get_logger),
    user_store: UserStore = Depends(deps.get_user_store),
):
    email = varification_data.email.lower()
    verification_code = varification_data.verification_code.upper()

    # Logging
    logger.info(f"verify_email called: {email}")

    # Check if user exists
    user = user_store.get_by_email(email)
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
        logger.error(f"Verification code does not match for user with email {email} - entered: {verification_code}")
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

    # Save updated user
    user_store.update(user.group, str(user.id), user.model_dump())

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
    user_store: UserStore = Depends(deps.get_user_store),
):
    # Check if user exists
    user = user_store.get_by_email(email)
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

        # Return error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_message
        )

    # Logging
    logger.info(f"Verification email resent: {user.email}")

    return JSONResponse(content={"message": "Verification email sent"})


@router.post("/password_reset/request")
async def password_reset_request(
    password_reset_request_data: Annotated[UserPasswordResetRequest, Depends()],
    logger: TLogger = Depends(deps.get_logger),
    user_store: UserStore = Depends(deps.get_user_store),
):
    email = password_reset_request_data.email.lower()

    # Logging
    logger.info(f"password_reset_request called: {email}")

    # Check if user exists
    user = user_store.get_by_email(email)
    if user is None:
        logger.error(f"User with email {email} does not exist")
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
    password_reset_code = shortuuid.ShortUUID().random(length=6).upper()
    user.password_reset_code = password_reset_code
    user.password_reset_code_expires_at = datetime.now(timezone.utc) + timedelta(
        hours=14
    )

    # Save updated user
    user_store.update(user.group, str(user.id), user.model_dump())

    # Generate password reset email
    # Generate URL with parameters
    password_reset_url_with_params = (
        str(settings.PASSWORD_RESET_URL)
        + "/?"
        + urllib.parse.urlencode(
            {"email": email, "password_reset_code": user.password_reset_code}
        )
    )
    try:
        # TODO: Implement password reset email sending
        logger.info(f"Password reset code for {email}: {password_reset_code}")
        pass
    except Exception as e:
        error_message = str(e)
        if hasattr(e, "message"):
            error_message = e.message

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
    user_store: UserStore = Depends(deps.get_user_store),
):
    email = form_data.email.lower()
    password_reset_code = form_data.password_reset_code.upper()
    new_password = form_data.new_password

    # Logging
    logger.info(f"password_reset_verify called: {email}")

    # Check if user exists
    user = user_store.get_by_email(email)
    if user is None:
        logger.error(f"User with email {email} does not exist")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed Data"
        )

    # Check if password reset code matches
    if user.password_reset_code != password_reset_code:
        logger.error(f"Password reset code does not match for user with email {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed Data"
        )

    # Check if password reset code has expired
    try:
        if user.password_reset_code_expires_at < datetime.now(timezone.utc):
            logger.error(f"Password reset code has expired for user with email {email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed Data"
            )
    except Exception as e:
        logger.error(f"Error checking password reset code expiration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed Data"
        )

    # Update user record
    user.password = get_password_hash(new_password)
    user.password_reset_code = None
    user.password_reset_code_expires_at = None

    # Save updated user
    user_store.update(user.group, str(user.id), user.model_dump())

    # Return an authentication token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    logger.info(f"Token generated : email: {user.email}, disabled: {user.disabled}")

    return JSONResponse(content={"access_token": access_token, "token_type": "bearer"})


@router.post("/update_profile")
async def update_profile(
    user_update: Annotated[UserUpdate, Body()],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    logger: TLogger = Depends(deps.get_logger),
    user_store: UserStore = Depends(deps.get_user_store),
):
    # Get the validated update data
    update_data = user_update.model_dump(exclude_unset=True)
    logger.info(f"update_data: {update_data}")
    # Remove any fields that shouldn't be updated
    update_data.pop("email", None)  # Email should not be updatable through this endpoint
    update_data.pop("group_id", None)  # Group should be updated through a different endpoint
    
    # Handle password hashing if password is being updated
    if "password" in update_data and update_data["password"] is not None:
        update_data["password"] = get_password_hash(update_data["password"])
    
    # Only proceed if there are actual fields to update
    if not update_data:
        return JSONResponse(content={"message": "No fields to update"})
    
    # Update user
    logger.info(f"update_profile called: {current_user.email} - {update_data}")
    updated_user = user_store.update(current_user.group, str(current_user.id), update_data)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Logging
    logger.info(f"Profile updated: {updated_user.email}")

    return JSONResponse(content={"message": "Profile updated successfully"})


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


@router.post("/invite")
async def invite_user(
    invite_data: Annotated[UserInvite, Depends()],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    logger: TLogger = Depends(deps.get_logger),
    user_store: UserStore = Depends(deps.get_user_store),
    group_store: GroupStore = Depends(deps.get_group_store),
):
    """
    Invite a user to join the current user's team. Creates the user with is_verified=False and stores the invite code in verification_code.
    """
    email = invite_data.email.lower()
    
    # Logging
    logger.info(f"invite_user called: {email} by {current_user.email}")

    # Check if user already exists
    existing_user = user_store.get_by_email(email)
    if existing_user is not None:
        logger.error(f"Attempting to invite existing user: {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )

    # Check if current user has a group
    if not current_user.group:
        logger.error(f"Current user {current_user.email} has no group")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must be part of a team to send invites"
        )

    # Verify the group exists
    group_data = group_store.get(current_user.group)
    if not group_data:
        logger.error(f"Group {current_user.group} does not exist")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid group"
        )

    # Generate invite code and expiry
    invite_code = shortuuid.ShortUUID().random(length=6).upper()
    invite_code_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    # Create the invited user (is_verified=False, no password, store invite code)
    user_id = uuid4()
    invited_user = User(
        id=user_id,
        email=email,
        password=None,
        disabled=False,
        created_at=datetime.now(timezone.utc),
        is_verified=False,
        verification_code=invite_code,
        verification_code_expires_at=invite_code_expires_at,
        group=current_user.group,
    )
    user_store.create(invited_user, current_user.group)

    # Send invite email (code is verification_code)
    try:
        inviter_name = current_user.full_name or current_user.email.split('@')[0]
        send_invite_email(
            email=email,
            inviter_name=inviter_name,
            group_id=current_user.group,
            invite_url=settings.INVITE_URL
        )
        logger.info(f"Invite sent successfully to {email} with code {invite_code}")
        return JSONResponse(content={
            "message": "Invitation sent successfully",
            "email": email
        })
    except Exception as e:
        error_message = str(e)
        if hasattr(e, "message"):
            error_message = e.message
        # Logging
        logger.error(f"Error sending invite email: {error_message}")
        # Rollback: delete the user
        user_store.delete(current_user.group, str(user_id))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to send invitation email"
        )


@router.get("/me", response_model=UserResponse)
async def read_user_me(
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    group_store: GroupStore = Depends(deps.get_group_store),
):
    """
    Get current user's profile information.
    """
    # Fetch group data if user has a group
    group_response = None
    if current_user.group:
        group_data = group_store.get(current_user.group)
        if group_data:
            group_response = GroupResponse.model_validate(group_data.model_dump())
    
    # Create UserResponse with proper group data, excluding sensitive fields
    user_response = UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        created_at=current_user.created_at or datetime.now(timezone.utc),
        last_login=current_user.last_login,
        is_verified=current_user.is_verified or False,
        disabled=current_user.disabled or False,
        group=group_response
    )
    
    return user_response


@router.get("/me/items")
async def read_own_items(
    current_user: Annotated[User, Depends(deps.get_current_active_user)]
):
    return JSONResponse(content=[{"item_id": "Foo", "owner": current_user.email}])


@router.get("/users/email/{email}", response_model=UserResponse)
async def get_user_via_email(
    email: str,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    logger: TLogger = Depends(deps.get_logger),
    user_store: UserStore = Depends(deps.get_user_store),
    group_store: GroupStore = Depends(deps.get_group_store),
    user_access: User = Depends(deps.owner_or_admin_for_user_by_email(deps.lookup_user_by_email))
):
    """
    Get a specific user by email.
    """
    try:
        # Get user by email using the email index
        user_data = user_store.get_by_email(email)
        
        if user_data is None:
            logger.info(f"User not found: {email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        # Fetch group data if user has a group
        group_response = None
        if user_data.group:
            group_data = group_store.get(user_data.group)
            if group_data:
                group_response = GroupResponse.model_validate(group_data.model_dump())
            
        # Check group matches unless user is admin
        if current_user.role != "admin" and user_data.group != current_user.group:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Convert user data to UserResponse model, ensuring UUID is converted to string
        user_response = UserResponse(
            id=str(user_data.id),  # Convert UUID to string
            email=user_data.email,
            full_name=user_data.full_name,
            created_at=user_data.created_at or datetime.now(timezone.utc),
            last_login=user_data.last_login,
            is_verified=user_data.is_verified or False,
            disabled=user_data.disabled or False,
            group=group_response
        )
            
        return JSONResponse(content=user_response.model_dump(mode="json"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user {email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user"
        )


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    logger: TLogger = Depends(deps.get_logger),
    user_store: UserStore = Depends(deps.get_user_store),
    group_store: GroupStore = Depends(deps.get_group_store),
):
    """
    List all users with pagination. Admin only.
    """
    
    # Check group ownership unless user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        # Get all users from store
        users, total = user_store.list(page=skip//limit + 1, limit=limit)
        logger.info(f"list_users called: {users}")
        
        # Convert User models to UserResponse with proper group data
        user_responses = []
        for user in users:
            # Fetch group data if user has a group
            group_response = None
            if user.group:
                group_data = group_store.get(user.group)
                if group_data:
                    group_response = GroupResponse.model_validate(group_data.model_dump())
            
            # Create UserResponse with proper group data
            user_response = UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                created_at=user.created_at or datetime.now(timezone.utc),
                last_login=user.last_login,
                is_verified=user.is_verified or False,
                disabled=user.disabled or False,
                group=group_response
            )
            user_responses.append(user_response.model_dump(mode="json"))
        
        return JSONResponse(content=user_responses)
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
    user_store: UserStore = Depends(deps.get_user_store),
    group_store: GroupStore = Depends(deps.get_group_store),
    user_access: User = Depends(deps.owner_or_admin_for_user(deps.lookup_user))
):
    """
    Get a specific user by UUID.
    """
    try:
        # Try to get user by UUID
        user_data = user_store.get_by_id_only(str(user_id))
        
        if user_data is None:
            logger.info(f"User not found: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        # Check group ownership unless user is admin
        if current_user.role != "admin" and user_data.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Fetch group data if user has a group
        group_response = None
        if user_data.group:
            group_data = group_store.get(user_data.group)
            if group_data:
                group_response = GroupResponse.model_validate(group_data.model_dump())
            
        # Convert user data to UserResponse model, ensuring UUID is converted to string
        user_response = UserResponse(
            id=str(user_data.id),  # Convert UUID to string
            email=user_data.email,
            full_name=user_data.full_name,
            created_at=user_data.created_at or datetime.now(timezone.utc),
            last_login=user_data.last_login,
            is_verified=user_data.is_verified or False,
            disabled=user_data.disabled or False,
            group=group_response
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


@router.post("/users", response_model=UserResponse)
async def create_user_admin(
    user_data: UserSignup,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    logger: TLogger = Depends(deps.get_logger),
    user_store: UserStore = Depends(deps.get_user_store),
    group_store: GroupStore = Depends(deps.get_group_store),
):
    """
    Create a new user (admin only).
    This is separate from the registration endpoint as it's for admin use.
    """
    # TODO: Add admin role check
    # TODO: group limits. 
    try:
        # Check if user already exists using email index
        existing_user = user_store.get_by_email(user_data.email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists"
            )
        
        # Check group ownership unless user is admin
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # For now, use default group
        # TODO: Allow specifying group in admin user creation
        default_group_id = "default"
        
        # Check if default group exists, create if not
        default_group = group_store.get(default_group_id)
        if not default_group:
            from app.schemas import GroupCreate
            group_data = GroupCreate(
                name="Default Group",
                description="Default group for new users"
            )
            default_group = group_store.create(group_data, "system")
            default_group_id = str(default_group.id)

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
            "group": default_group_id,
        })

        # Store user with group structure
        user_store.create(user, default_group_id)
        
        logger.info(f"Admin created user: {user.email} with ID {user.id}")
        
        # Fetch group data for the response
        group_response = None
        if user.group:
            group_data = group_store.get(user.group)
            if group_data:
                group_response = GroupResponse.model_validate(group_data.model_dump())
        
        # Create UserResponse with proper group data
        user_response = UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            created_at=user.created_at or datetime.now(timezone.utc),
            last_login=user.last_login,
            is_verified=user.is_verified or False,
            disabled=user.disabled or False,
            group=group_response
        )
        
        return JSONResponse(content=user_response.model_dump(mode="json"))
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
    user_store: UserStore = Depends(deps.get_user_store),
    group_store: GroupStore = Depends(deps.get_group_store),
    user_access: User = Depends(deps.owner_or_admin_for_user(deps.lookup_user))
):
    """
    Update a user's details (admin or self).
    """
    try:
        user_data = user_store.get_by_id_only(str(user_id))
        if user_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user = User.model_validate(user_data)
        
        # Check group ownership unless user is admin
        if current_user.role != "admin" and user_data.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Update user fields
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "password" and value is not None:
                value = get_password_hash(value)
            setattr(user, field, value)

        # Update user with group structure
        user_store.update(user.group, str(user.id), user.model_dump())
        
        logger.info(f"Updated user: {user.email} with ID {user.id}")
        
        # Fetch group data if user has a group
        group_response = None
        if user.group:
            group_data = group_store.get(user.group)
            if group_data:
                group_response = GroupResponse.model_validate(group_data.model_dump())
        
        # Create UserResponse with proper group data
        user_response = UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            created_at=user.created_at or datetime.now(timezone.utc),
            last_login=user.last_login,
            is_verified=user.is_verified or False,
            disabled=user.disabled or False,
            group=group_response
        )
        
        return JSONResponse(content=user_response.model_dump(mode="json"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user"
        )

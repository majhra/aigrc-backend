import json
from os.path import join
from typing import Any, List
from urllib.parse import urljoin

from pydantic import AnyHttpUrl, EmailStr, field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


# Monkey patch the `decode_complex_value` method from PydanticBaseSettingsSource
# to handle the ORIGINS field
# https://github.com/pydantic/pydantic-settings/issues/126
def decode_complex_value(self, field_name: str, field: FieldInfo, value: Any) -> Any:
    if field_name == "ORIGINS":
        if isinstance(value, str) and not value.startswith("["):
            return [i.strip() for i in value.split(",")]

    return json.loads(value)


PydanticBaseSettingsSource.decode_complex_value = decode_complex_value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    PROJECT_NAME: str = "AI GRC"
    API_V1_STR: str = "/api/v1.0"

    # Variables which should be set in .env file
    GITLAB_ENVIRONMENT: str | None = None
    ORIGINS: List[AnyHttpUrl] = [
        AnyHttpUrl("http://localhost"),
        AnyHttpUrl("http://localhost:3000"),
    ]
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REDIS_ADDRESS: str = "localhost"
    REDIS_PORT: int = 6379
    
    # Database configuration
    DATABASE_URL: str = ""
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False
    SES_AWS_ACCESS_KEY_ID: str = ""
    SES_AWS_SECRET_ACCESS_KEY: str = ""
    SES_AWS_SENDER_EMAIL: EmailStr = ""
    SES_AWS_REGION: str = "ap-southeast-2"
    FRONTEND_URL_BASE: AnyHttpUrl = AnyHttpUrl("http://localhost:3000")
    SUPPORT_EMAIL: EmailStr = ""
    UNLEASH_URL: AnyHttpUrl | None = None
    UNLEASH_INSTANCE_ID: str | None = None

    # Rate limiting configuration
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_USE_REDIS: bool = False  # Set to True for distributed rate limiting
    # Login rate limits
    RATE_LIMIT_LOGIN_REQUESTS: int = 5
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 60
    RATE_LIMIT_LOGIN_BLOCK_SECONDS: int = 300
    # Registration rate limits
    RATE_LIMIT_REGISTRATION_REQUESTS: int = 3
    RATE_LIMIT_REGISTRATION_WINDOW_SECONDS: int = 3600
    RATE_LIMIT_REGISTRATION_BLOCK_SECONDS: int = 3600
    # Password reset rate limits
    RATE_LIMIT_PASSWORD_RESET_REQUESTS: int = 3
    RATE_LIMIT_PASSWORD_RESET_WINDOW_SECONDS: int = 3600
    RATE_LIMIT_PASSWORD_RESET_BLOCK_SECONDS: int = 1800
    # AI connection test rate limits
    RATE_LIMIT_AI_TEST_REQUESTS: int = 10
    RATE_LIMIT_AI_TEST_WINDOW_SECONDS: int = 60
    RATE_LIMIT_AI_TEST_BLOCK_SECONDS: int = 60

    # Variables which probably shouldn't be set in .env file (but they can be if you want)
    ASSETS_DIR: str = join("app", "assets")
    FRONTEND_URL_PATH_VERIFICATION: str = "/auth/verification"
    FRONTEND_URL_PATH_PASSWORD_RESET: str = "/auth/password-reset"
    FRONTEND_URL_PATH_INVITE: str = "/auth/invite"
    MIN_PASSWORD_LENGTH: int = 8

    # Custom validators
    @field_validator(
        "SES_AWS_ACCESS_KEY_ID",
        "SES_AWS_SECRET_ACCESS_KEY",
        "SES_AWS_SENDER_EMAIL",
        "SECRET_KEY",
        "SUPPORT_EMAIL",
        "DATABASE_URL",
    )
    def compulsory_string_not_empty(cls, value: str) -> str:
        assert value != "", "Variable is not set"
        return value

    # Variables which are derived from other variables
    @property
    def VERIFICATION_URL(self) -> AnyHttpUrl:
        return AnyHttpUrl(
            urljoin(str(self.FRONTEND_URL_BASE), self.FRONTEND_URL_PATH_VERIFICATION)
        )

    @property
    def PASSWORD_RESET_URL(self) -> AnyHttpUrl:
        return AnyHttpUrl(
            urljoin(str(self.FRONTEND_URL_BASE), self.FRONTEND_URL_PATH_PASSWORD_RESET)
        )

    @property
    def INVITE_URL(self) -> AnyHttpUrl:
        return AnyHttpUrl(
            urljoin(str(self.FRONTEND_URL_BASE), self.FRONTEND_URL_PATH_INVITE)
        )


settings = Settings()

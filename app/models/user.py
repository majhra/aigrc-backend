from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class Group(Base):
    __tablename__ = "groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    status = Column(String(20), nullable=False, default="ACTIVE")  # ACTIVE, INACTIVE, SUSPENDED
    settings = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    users = relationship("User", back_populates="group")
    tests = relationship("AITest", back_populates="group")
    configurations = relationship("AIConfiguration", back_populates="group")
    prompts = relationship("Prompt", back_populates="group")
    prompt_categories = relationship("PromptCategory", back_populates="group")
    test_executions = relationship("TestExecution", back_populates="group")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    password = Column(String(255), nullable=False)
    disabled = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    role = Column(String(50))
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True))
    verification_code = Column(String(255))
    verification_code_expires_at = Column(DateTime(timezone=True))
    password_reset_code = Column(String(255))
    password_reset_code_expires_at = Column(DateTime(timezone=True))

    # Relationships
    group = relationship("Group", back_populates="users")
    created_tests = relationship("AITest", back_populates="creator", foreign_keys="AITest.created_by")
    executed_tests = relationship("TestExecution", back_populates="executor")
    created_prompts = relationship("Prompt", back_populates="creator")
    created_prompt_categories = relationship("PromptCategory", back_populates="creator")
    created_configurations = relationship("AIConfiguration", back_populates="creator")
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class AIConfiguration(Base):
    __tablename__ = "ai_configurations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    provider = Column(String(50), nullable=False)  # openai, anthropic, azure_openai, google, huggingface, custom
    endpoint_url = Column(String(512))
    auth_type = Column(String(30), nullable=False)  # api_key, bearer_token, oauth, azure_ad
    model_name = Column(String(255))
    tags = Column(JSON)  # Array of strings
    status = Column(String(20), nullable=False, default="active")  # active, inactive, testing
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_tested_at = Column(DateTime(timezone=True))
    last_test_status = Column(String(20))  # success, failed, pending
    last_test_error = Column(Text)
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    
    # Sensitive data stored separately (encrypted)
    api_key_encrypted = Column(Text)
    azure_api_version = Column(String(50))
    custom_headers = Column(JSON)

    # Relationships
    creator = relationship("User", back_populates="created_configurations")
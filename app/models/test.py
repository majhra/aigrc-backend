from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class AITest(Base):
    __tablename__ = "ai_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    prompt_template = Column(Text)
    interface_type = Column(String(30), nullable=False)  # DIRECT_LLM, CHATBOT, PLUGIN_ENABLED, CUSTOM_APP
    connection_config = Column(JSON)  # ConnectionConfig object
    validation_config = Column(JSON)  # ValidationConfig object
    tags = Column(JSON)  # Array of strings
    risk_level = Column(String(10), nullable=False)  # LOW, MEDIUM, HIGH
    status = Column(String(20), nullable=False, default="DRAFT")  # DRAFT, ACTIVE, ARCHIVED
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_run_at = Column(DateTime(timezone=True))
    latest_execution_id = Column(UUID(as_uuid=True))

    # Relationships
    creator = relationship("User", back_populates="created_tests")
    group = relationship("Group", back_populates="tests")
    executions = relationship("TestExecution", back_populates="test", foreign_keys="TestExecution.test_id")


class TestExecution(Base):
    __tablename__ = "test_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id = Column(UUID(as_uuid=True), ForeignKey("ai_tests.id"), index=True)
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    executed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    execution_environment = Column(JSON)  # ExecutionEnvironment object
    input_variables = Column(JSON)  # Dict[str, str]
    prompt = Column(Text)
    response = Column(Text)
    benchmarks = Column(JSON)  # PerformanceMetrics object
    validation_status = Column(String(20), nullable=False, default="PENDING", index=True)  # PENDING, IN_PROGRESS, VALIDATED, ERROR
    validations = Column(JSON)  # Array of ValidationEvent objects
    error = Column(JSON)  # ErrorDetails object

    # Relationships
    test = relationship("AITest", back_populates="executions", foreign_keys=[test_id])
    executor = relationship("User", back_populates="executed_tests")
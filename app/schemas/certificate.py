"""
Pydantic v2 schemas for request validation, job status tracking, and API responses.
"""
import re
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.db.models import JobStatus, ItemStatus


# Email validation regex pattern (RFC 5322 compliant subset)
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class RecipientInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Full name of the certificate recipient")
    email: Optional[str] = Field(None, description="Optional email of the recipient")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Recipient name cannot be empty or whitespace only.")
        return stripped

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            return None
        if not EMAIL_REGEX.match(stripped):
            raise ValueError(f"Invalid email address format: '{v}'")
        return stripped.lower()


class CertificateGenerateRequest(BaseModel):
    course_name: str = Field(..., min_length=1, max_length=255, description="Name of the course, workshop, or event")
    issue_date: str = Field(..., min_length=1, max_length=50, description="Date of issuance (e.g. 2026-10-07)")
    recipients: List[RecipientInput] = Field(..., min_length=1, description="List of recipients (at least 1 required)")

    @field_validator("course_name")
    @classmethod
    def validate_course_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Course name cannot be empty or whitespace only.")
        return stripped

    @field_validator("issue_date")
    @classmethod
    def validate_issue_date(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Issue date cannot be empty or whitespace only.")
        return stripped


class GenerateJobAcceptedResponse(BaseModel):
    job_id: str
    status: JobStatus
    total_count: int
    message: str


class CertificateItemResponse(BaseModel):
    id: str
    certificate_id: str
    recipient_name: str
    recipient_email: Optional[str] = None
    status: ItemStatus
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    job_id: str
    course_name: str
    issue_date: str
    status: JobStatus
    total: int
    completed: int
    failed: int
    pending: int
    progress_percentage: float
    created_at: datetime
    completed_at: Optional[datetime] = None
    download_all_url: Optional[str] = None
    items: List[CertificateItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class CertificateVerifyResponse(BaseModel):
    certificate_id: str
    recipient_name: str
    course_name: str
    issue_date: str
    status: str = "VALID"
    issued_at: datetime
    download_url: Optional[str] = None

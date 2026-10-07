"""
Tests covering Pydantic schema validation and request sanitization.
"""
import pytest
from fastapi.testclient import TestClient


def test_empty_request_body(client: TestClient):
    """Submitting empty payload should return 422 validation error."""
    response = client.post("/api/v1/certificates/generate", json={})
    assert response.status_code == 422


def test_missing_course_name(client: TestClient):
    """Missing or blank course name must be rejected."""
    payload = {
        "course_name": "   ",
        "issue_date": "2026-10-07",
        "recipients": [{"name": "John Doe", "email": "john@example.com"}],
    }
    response = client.post("/api/v1/certificates/generate", json=payload)
    assert response.status_code == 422
    assert "Course name cannot be empty" in response.text


def test_missing_issue_date(client: TestClient):
    """Missing or blank issue date must be rejected."""
    payload = {
        "course_name": "Python Mastery",
        "issue_date": "   ",
        "recipients": [{"name": "John Doe", "email": "john@example.com"}],
    }
    response = client.post("/api/v1/certificates/generate", json=payload)
    assert response.status_code == 422
    assert "Issue date cannot be empty" in response.text


def test_empty_recipients_list(client: TestClient):
    """An empty recipients list must be rejected."""
    payload = {
        "course_name": "Python Mastery",
        "issue_date": "2026-10-07",
        "recipients": [],
    }
    response = client.post("/api/v1/certificates/generate", json=payload)
    assert response.status_code == 422


def test_empty_recipient_name(client: TestClient):
    """A recipient with whitespace/empty name must be rejected."""
    payload = {
        "course_name": "Python Mastery",
        "issue_date": "2026-10-07",
        "recipients": [{"name": "  ", "email": "john@example.com"}],
    }
    response = client.post("/api/v1/certificates/generate", json=payload)
    assert response.status_code == 422
    assert "Recipient name cannot be empty" in response.text


def test_invalid_recipient_email_format(client: TestClient):
    """A malformed email address must be rejected."""
    payload = {
        "course_name": "Python Mastery",
        "issue_date": "2026-10-07",
        "recipients": [{"name": "John Doe", "email": "not-an-email-format"}],
    }
    response = client.post("/api/v1/certificates/generate", json=payload)
    assert response.status_code == 422
    assert "Invalid email address format" in response.text


def test_valid_request_without_email(client: TestClient):
    """Recipients without optional email should pass validation smoothly."""
    payload = {
        "course_name": "Python Mastery",
        "issue_date": "2026-10-07",
        "recipients": [{"name": "Jane Doe"}],
    }
    response = client.post("/api/v1/certificates/generate", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["total_count"] == 1

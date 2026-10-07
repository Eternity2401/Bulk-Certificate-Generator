"""
End-to-End API tests covering job generation, progress polling, PDF download,
ZIP batch archive download, and verification portal.
"""
import zipfile
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.db.models import Job, CertificateItem, JobStatus, ItemStatus
from app.services.certificate_service import process_certificate_job


def test_create_and_process_job_e2e(client: TestClient, db_session: Session):
    """
    Complete end-to-end flow:
    1. Submit generation request
    2. Synchronously run the worker
    3. Verify status, item results, PDF file generation
    """
    payload = {
        "course_name": "Distributed Backend Architecture",
        "issue_date": "2026-10-07",
        "recipients": [
            {"name": "Alice Wonderland", "email": "alice@example.com"},
            {"name": "Bob Builder", "email": "bob@example.com"},
        ],
    }

    # Step 1: Submit job
    res = client.post("/api/v1/certificates/generate", json=payload)
    assert res.status_code == 202
    data = res.json()
    job_id = data["job_id"]
    assert data["total_count"] == 2
    assert data["status"] == "PENDING"

    # Step 2: Execute background processing worker with test session
    process_certificate_job(job_id, db=db_session)

    # Step 3: Fetch updated job status
    status_res = client.get(f"/api/v1/certificates/jobs/{job_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["status"] == "COMPLETED"
    assert status_data["total"] == 2
    assert status_data["completed"] == 2
    assert status_data["failed"] == 0
    assert status_data["pending"] == 0
    assert status_data["progress_percentage"] == 100.0
    assert len(status_data["items"]) == 2

    # Step 4: Test Individual Download
    first_item = status_data["items"][0]
    assert first_item["status"] == "COMPLETED"
    assert first_item["download_url"] is not None

    download_res = client.get(first_item["download_url"])
    assert download_res.status_code == 200
    assert download_res.headers["content-type"] == "application/pdf"
    assert download_res.content[:5] == b"%PDF-"

    # Step 5: Test Download All ZIP
    zip_res = client.get(f"/api/v1/certificates/jobs/{job_id}/download-all")
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"

    # Verify ZIP contents
    with zipfile.ZipFile(io.BytesIO(zip_res.content)) as zf:
        file_list = zf.namelist()
        assert len(file_list) == 2
        for fname in file_list:
            assert fname.endswith(".pdf")

    # Step 6: Test Verification Endpoint (JSON)
    cert_id = first_item["certificate_id"]
    verify_res = client.get(f"/api/v1/certificates/verify/{cert_id}")
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["certificate_id"] == cert_id
    assert verify_data["recipient_name"] == "Alice Wonderland"
    assert verify_data["status"] == "VALID"

    # Step 7: Test Verification Endpoint (HTML browser view)
    verify_html_res = client.get(
        f"/api/v1/certificates/verify/{cert_id}",
        headers={"Accept": "text/html"},
    )
    assert verify_html_res.status_code == 200
    assert "AUTHENTIC" in verify_html_res.text
    assert "Alice Wonderland" in verify_html_res.text


def test_individual_failure_isolation(client: TestClient, db_session: Session):
    """
    Verify that an exception generating one certificate does not prevent
    other valid certificates from completing successfully.
    """
    payload = {
        "course_name": "Fault Tolerance 101",
        "issue_date": "2026-10-07",
        "recipients": [
            {"name": "Valid Recipient One", "email": "valid1@example.com"},
            {"name": "Trigger Failure", "email": "fail@example.com"},
            {"name": "Valid Recipient Two", "email": "valid2@example.com"},
        ],
    }

    res = client.post("/api/v1/certificates/generate", json=payload)
    assert res.status_code == 202
    job_id = res.json()["job_id"]

    # Invalidate recipient name on the second item in DB to trigger isolated exception
    items = db_session.query(CertificateItem).filter(CertificateItem.job_id == job_id).all()
    items[1].recipient_name = ""  # Empty name will fail validation in worker
    db_session.commit()

    # Process job with test session
    process_certificate_job(job_id, db=db_session)

    # Check status
    status_res = client.get(f"/api/v1/certificates/jobs/{job_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()

    # Overall job must be COMPLETED_WITH_ERRORS
    assert status_data["status"] == "COMPLETED_WITH_ERRORS"
    assert status_data["total"] == 3
    assert status_data["completed"] == 2
    assert status_data["failed"] == 1

    # Check item statuses
    res_items = status_data["items"]
    assert res_items[0]["status"] == "COMPLETED"
    assert res_items[1]["status"] == "FAILED"
    assert "Generation failed" in res_items[1]["error_message"]
    assert res_items[2]["status"] == "COMPLETED"


def test_non_existent_job_404(client: TestClient):
    """Querying a missing job ID should return 404."""
    res = client.get("/api/v1/certificates/jobs/non-existent-uuid")
    assert res.status_code == 404


def test_non_existent_certificate_download_404(client: TestClient):
    """Downloading a missing certificate item ID should return 404."""
    res = client.get("/api/v1/certificates/non-existent-item/download")
    assert res.status_code == 404


def test_non_existent_certificate_verify_404(client: TestClient):
    """Verifying a missing certificate ID should return 404 for JSON."""
    res = client.get("/api/v1/certificates/verify/CERT-INVALID-0000")
    assert res.status_code == 404


def test_health_check(client: TestClient):
    """Health check endpoint should return 200 with service info."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"

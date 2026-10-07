"""
API Route Handlers for Bulk Certificate Generation, Status Tracking,
PDF Downloads, Batch ZIP Retrieval, and Public Certificate Verification.
"""
import io
import uuid
import secrets
import string
import zipfile
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, status
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db
from app.db.models import Job, CertificateItem, JobStatus, ItemStatus
from app.schemas.certificate import (
    CertificateGenerateRequest,
    GenerateJobAcceptedResponse,
    JobStatusResponse,
    CertificateItemResponse,
    CertificateVerifyResponse,
)
from app.services.certificate_service import process_certificate_job

router = APIRouter(prefix="/api/v1/certificates", tags=["Certificates"])

# Jinja2 template setup for HTML verification page
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "app" / "templates"))


def generate_unique_cert_id() -> str:
    """Generates a readable, unique certificate identifier e.g. CERT-A1B2-C3D4."""
    charset = string.ascii_uppercase + string.digits
    part1 = "".join(secrets.choice(charset) for _ in range(4))
    part2 = "".join(secrets.choice(charset) for _ in range(4))
    return f"CERT-{part1}-{part2}"


@router.post(
    "/generate",
    response_model=GenerateJobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit bulk certificate generation request",
)
def create_certificate_job(
    payload: CertificateGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Accepts a bulk certificate generation request, initializes the job and items in the database,
    and enqueues background processing via FastAPI BackgroundTasks.
    """
    job_id = str(uuid.uuid4())
    total_recipients = len(payload.recipients)

    # 1. Create Job record
    new_job = Job(
        id=job_id,
        course_name=payload.course_name,
        issue_date=payload.issue_date,
        status=JobStatus.PENDING,
        total_count=total_recipients,
        success_count=0,
        failed_count=0,
    )
    db.add(new_job)

    # 2. Create CertificateItem records for each recipient
    for recipient in payload.recipients:
        cert_id = generate_unique_cert_id()
        item = CertificateItem(
            id=str(uuid.uuid4()),
            job_id=job_id,
            certificate_id=cert_id,
            recipient_name=recipient.name,
            recipient_email=recipient.email,
            status=ItemStatus.PENDING,
        )
        db.add(item)

    db.commit()

    # 3. Enqueue background task
    background_tasks.add_task(process_certificate_job, job_id)

    return GenerateJobAcceptedResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        total_count=total_recipients,
        message="Certificate generation job accepted and scheduled for background processing.",
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job progress, counters, and recipient items",
)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Retrieves the status, progress percentage, completion counters,
    and individual recipient results for a certificate generation job.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job with ID '{job_id}' not found.")

    processed = job.success_count + job.failed_count
    pending = max(0, job.total_count - processed)
    progress_percentage = round((processed / job.total_count) * 100, 1) if job.total_count > 0 else 0.0

    items_response = []
    for item in job.items:
        download_url = f"/api/v1/certificates/{item.id}/download" if item.status == ItemStatus.COMPLETED else None
        items_response.append(
            CertificateItemResponse(
                id=item.id,
                certificate_id=item.certificate_id,
                recipient_name=item.recipient_name,
                recipient_email=item.recipient_email,
                status=item.status,
                download_url=download_url,
                error_message=item.error_message,
                created_at=item.created_at,
            )
        )

    download_all_url = f"/api/v1/certificates/jobs/{job.id}/download-all" if job.success_count > 0 else None

    return JobStatusResponse(
        job_id=job.id,
        course_name=job.course_name,
        issue_date=job.issue_date,
        status=job.status,
        total=job.total_count,
        completed=job.success_count,
        failed=job.failed_count,
        pending=pending,
        progress_percentage=progress_percentage,
        created_at=job.created_at,
        completed_at=job.completed_at,
        download_all_url=download_all_url,
        items=items_response,
    )


@router.get(
    "/{item_id}/download",
    summary="Download an individual generated PDF certificate",
)
def download_certificate(item_id: str, db: Session = Depends(get_db)):
    """
    Streams the generated PDF file for a specific certificate item.
    """
    item = db.query(CertificateItem).filter(CertificateItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Certificate item '{item_id}' not found.")

    if item.status != ItemStatus.COMPLETED or not item.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Certificate is not ready for download. Current status: {item.status}",
        )

    full_path = settings.BASE_DIR / item.file_path
    if not full_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate file missing on server disk.")

    return FileResponse(
        path=str(full_path),
        media_type="application/pdf",
        filename=full_path.name,
    )


@router.get(
    "/jobs/{job_id}/download-all",
    summary="Download all generated certificates for a job as a ZIP archive",
)
def download_all_certificates(job_id: str, db: Session = Depends(get_db)):
    """
    Bundles all successfully generated PDF certificates for the given job into a ZIP archive.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job with ID '{job_id}' not found.")

    completed_items = [
        item for item in job.items if item.status == ItemStatus.COMPLETED and item.file_path
    ]

    if not completed_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No completed certificates found for this job yet.",
        )

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for item in completed_items:
            full_path = settings.BASE_DIR / item.file_path
            if full_path.exists():
                zip_file.write(full_path, arcname=full_path.name)

    zip_buffer.seek(0)
    zip_filename = f"certificates_{job.id[:8]}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )


@router.get(
    "/verify/{certificate_id}",
    summary="Verify certificate authenticity by unique certificate ID",
)
def verify_certificate(
    certificate_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Looks up certificate information by certificate ID.
    Returns JSON for API clients or renders an authentic HTML certificate verification badge.
    """
    item = (
        db.query(CertificateItem)
        .filter(CertificateItem.certificate_id == certificate_id)
        .first()
    )

    accept_header = request.headers.get("accept", "")
    is_html_request = "text/html" in accept_header

    if not item or item.status != ItemStatus.COMPLETED:
        if is_html_request:
            return templates.TemplateResponse(
                request,
                "verify.html",
                context={
                    "is_valid": False,
                    "certificate_id": certificate_id,
                    "message": "Certificate record not found or generation was incomplete.",
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate ID '{certificate_id}' is invalid or not verified.",
        )

    job = item.job
    download_url = f"/api/v1/certificates/{item.id}/download"

    if is_html_request:
        return templates.TemplateResponse(
            request,
            "verify.html",
            context={
                "is_valid": True,
                "certificate_id": item.certificate_id,
                "recipient_name": item.recipient_name,
                "recipient_email": item.recipient_email or "Not Provided",
                "course_name": job.course_name if job else "N/A",
                "issue_date": job.issue_date if job else "N/A",
                "issued_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "download_url": download_url,
            },
        )

    return CertificateVerifyResponse(
        certificate_id=item.certificate_id,
        recipient_name=item.recipient_name,
        course_name=job.course_name if job else "N/A",
        issue_date=job.issue_date if job else "N/A",
        status="VALID",
        issued_at=item.created_at,
        download_url=download_url,
    )

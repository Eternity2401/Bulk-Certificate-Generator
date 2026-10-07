"""
Certificate Job Orchestrator & Background Worker.
Handles asynchronous generation with per-recipient error isolation,
real-time database state updates, and job completion aggregation.
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.db.database import SessionLocal
from app.db.models import Job, CertificateItem, JobStatus, ItemStatus
from app.services.pdf_service import generate_certificate_pdf


def sanitize_filename(name: str) -> str:
    """Sanitizes recipient name to produce a safe filesystem filename."""
    clean = re.sub(r"[^\w\-_]", "_", name.strip())
    return clean[:50] or "recipient"


def process_certificate_job(job_id: str, db: Optional[Session] = None) -> None:
    """
    Background worker function executed asynchronously by FastAPI BackgroundTasks.
    Iterates through all items in a job, isolates generation errors per recipient,
    and updates the database counters and overall job status.

    Args:
        job_id: UUID of the job to process.
        db: Optional existing SQLAlchemy session (e.g. for testing).
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        # Transition job to PROCESSING
        job.status = JobStatus.PROCESSING
        db.commit()

        job_dir = settings.STORAGE_DIR / job.id
        job_dir.mkdir(parents=True, exist_ok=True)

        items = db.query(CertificateItem).filter(CertificateItem.job_id == job.id).all()

        for item in items:
            item.status = ItemStatus.PROCESSING
            db.commit()

            try:
                # Sanity check on recipient name
                if not item.recipient_name or not item.recipient_name.strip():
                    raise ValueError("Recipient name is empty or invalid.")

                clean_name = sanitize_filename(item.recipient_name)
                pdf_filename = f"{item.certificate_id}_{clean_name}.pdf"
                pdf_path = job_dir / pdf_filename

                # Generate the ReportLab vector PDF with embedded QR code
                generate_certificate_pdf(
                    file_path=pdf_path,
                    recipient_name=item.recipient_name,
                    course_name=job.course_name,
                    issue_date=job.issue_date,
                    certificate_id=item.certificate_id,
                )

                # Relative path from project root for portability
                relative_path = pdf_path.relative_to(settings.BASE_DIR)
                item.file_path = str(relative_path).replace("\\", "/")
                item.status = ItemStatus.COMPLETED
                item.error_message = None
                job.success_count += 1

            except Exception as e:
                # Isolate failure: Record error message and update failed count
                item.status = ItemStatus.FAILED
                item.error_message = f"Generation failed: {str(e)}"
                job.failed_count += 1

            db.commit()

        # Finalize job status
        job.completed_at = datetime.utcnow()
        if job.failed_count == 0:
            job.status = JobStatus.COMPLETED
        elif job.success_count > 0:
            job.status = JobStatus.COMPLETED_WITH_ERRORS
        else:
            job.status = JobStatus.FAILED

        db.commit()

    finally:
        if should_close:
            db.close()

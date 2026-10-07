"""
PDF Certificate Generation Service using ReportLab.
Generates an elegant, professional landscape PDF certificate with vector graphics,
custom typography, unique certificate ID, and embedded verification QR code.
"""
from pathlib import Path
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from app.services.qr_service import generate_qr_code
from app.config import settings


def generate_certificate_pdf(
    file_path: Path,
    recipient_name: str,
    course_name: str,
    issue_date: str,
    certificate_id: str,
) -> Path:
    """
    Renders a single PDF certificate onto disk.

    Args:
        file_path: Absolute destination path for the PDF.
        recipient_name: Name of the recipient.
        course_name: Name of the event or course.
        issue_date: Formatted issue date string.
        certificate_id: Unique certificate code.

    Returns:
        Path to the written PDF file.
    """
    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Page setup: Landscape A4
    page_width, page_height = landscape(A4)
    c = canvas.Canvas(str(file_path), pagesize=landscape(A4))

    # --- Background & Borders ---
    # Outer background (soft parchment off-white)
    c.setFillColor(colors.HexColor("#f8fafc"))
    c.rect(0, 0, page_width, page_height, fill=True, stroke=False)

    # Outer decorative border (Deep Navy)
    c.setStrokeColor(colors.HexColor("#0f172a"))
    c.setLineWidth(4)
    c.rect(24, 24, page_width - 48, page_height - 48)

    # Inner decorative border (Warm Gold)
    c.setStrokeColor(colors.HexColor("#d97706"))
    c.setLineWidth(1.5)
    c.rect(32, 32, page_width - 64, page_height - 64)

    # Corner decorative accents
    corner_size = 18
    c.setFillColor(colors.HexColor("#d97706"))
    # Top-Left, Top-Right, Bottom-Left, Bottom-Right accents
    c.rect(32, page_height - 32 - corner_size, corner_size, corner_size, fill=True, stroke=False)
    c.rect(page_width - 32 - corner_size, page_height - 32 - corner_size, corner_size, corner_size, fill=True, stroke=False)
    c.rect(32, 32, corner_size, corner_size, fill=True, stroke=False)
    c.rect(page_width - 32 - corner_size, 32, corner_size, corner_size, fill=True, stroke=False)

    center_x = page_width / 2.0

    # --- Header Section ---
    c.setFillColor(colors.HexColor("#d97706"))
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(center_x, page_height - 75, "OFFICIAL RECOGNITION")

    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(center_x, page_height - 110, "CERTIFICATE OF COMPLETION")

    c.setStrokeColor(colors.HexColor("#d97706"))
    c.setLineWidth(1)
    c.line(center_x - 120, page_height - 122, center_x + 120, page_height - 122)

    # --- Recipient Section ---
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 12)
    c.drawCentredString(center_x, page_height - 155, "THIS CERTIFICATE IS PROUDLY PRESENTED TO")

    # Recipient Name in prominent bold typography
    c.setFillColor(colors.HexColor("#1e293b"))
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(center_x, page_height - 195, recipient_name)

    # Underline accent for recipient name
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setLineWidth(1)
    c.line(center_x - 180, page_height - 205, center_x + 180, page_height - 205)

    # --- Course & Achievement Section ---
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 12)
    c.drawCentredString(center_x, page_height - 235, "for successfully completing the requirements of")

    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(center_x, page_height - 268, course_name)

    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica", 11)
    c.drawCentredString(center_x, page_height - 295, f"Issued on {issue_date}")

    # --- Bottom Footer Section: Signatures & QR Code ---
    # 1. Left: Signatory Block
    sig_x = 100
    sig_y = 95
    c.setStrokeColor(colors.HexColor("#94a3b8"))
    c.setLineWidth(1)
    c.line(sig_x, sig_y + 20, sig_x + 160, sig_y + 20)
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(sig_x + 20, sig_y + 8, "Authorized Signature")
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 8)
    c.drawString(sig_x + 20, sig_y - 4, "Academic & Certification Board")

    # 2. Right: Verification QR Code & Certificate ID
    qr_url = f"{settings.BASE_URL}/api/v1/certificates/verify/{certificate_id}"
    qr_buffer = generate_qr_code(qr_url)
    qr_image = ImageReader(qr_buffer)

    qr_x = page_width - 170
    qr_y = 65
    qr_size = 70
    c.drawImage(qr_image, qr_x, qr_y, width=qr_size, height=qr_size)

    # QR Label & Certificate ID
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(qr_x - 120, qr_y + 45, "Scan to Verify:")
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 8)
    c.drawString(qr_x - 120, qr_y + 30, f"ID: {certificate_id}")
    c.drawString(qr_x - 120, qr_y + 16, "Official Verified Record")

    c.save()
    return file_path

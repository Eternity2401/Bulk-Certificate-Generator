"""
Tests covering isolated PDF rendering, QR code generation, and filename sanitization.
"""
from pathlib import Path
from app.services.qr_service import generate_qr_code
from app.services.pdf_service import generate_certificate_pdf
from app.services.certificate_service import sanitize_filename
from app.config import settings, Settings


def test_qr_code_generation():
    """Verify QR code generates a valid in-memory PNG image stream."""
    buffer = generate_qr_code("http://192.168.1.9:8000/api/v1/certificates/verify/CERT-123")
    data = buffer.getvalue()
    assert len(data) > 100
    # PNG signature check: \x89PNG\r\n\x1a\n
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


def test_base_url_configuration_and_trailing_slash_cleaning():
    """Verify Settings properly cleans and formats custom BASE_URL without trailing slashes."""
    custom_settings = Settings(BASE_URL="http://192.168.1.9:8000/ ")
    assert custom_settings.BASE_URL == "http://192.168.1.9:8000"

    expected_qr_url = f"{custom_settings.BASE_URL}/api/v1/certificates/verify/CERT-TEST-9999"
    assert expected_qr_url == "http://192.168.1.9:8000/api/v1/certificates/verify/CERT-TEST-9999"


def test_pdf_generation_creates_valid_file(tmp_path: Path):
    """Verify ReportLab produces an authentic vector PDF certificate."""
    test_pdf = tmp_path / "test_cert.pdf"
    result = generate_certificate_pdf(
        file_path=test_pdf,
        recipient_name="Ada Lovelace",
        course_name="Computer Science Pioneers",
        issue_date="2026-10-07",
        certificate_id="CERT-TEST-0001",
    )
    assert result.exists()
    assert result.is_file()
    assert result.stat().st_size > 1024  # > 1KB

    # PDF header check: %PDF-
    with open(result, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-"


def test_sanitize_filename():
    """Verify malicious or special characters in recipient names are sanitized."""
    assert sanitize_filename("John Doe") == "John_Doe"
    assert sanitize_filename("Jane/Doe\\Special:File*") == "Jane_Doe_Special_File_"
    assert sanitize_filename("   ") == "recipient"

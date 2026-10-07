"""
QR Code generation service.
Generates an in-memory PNG QR code for certificate verification URLs.
"""
import io
import qrcode
from qrcode.image.pil import PilImage


def generate_qr_code(verification_url: str) -> io.BytesIO:
    """
    Generates a QR code image as an in-memory BytesIO PNG buffer.
    
    Args:
        verification_url: The full URL where the certificate can be verified.
        
    Returns:
        io.BytesIO buffer containing the PNG image.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(verification_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#1e293b", back_color="#ffffff")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

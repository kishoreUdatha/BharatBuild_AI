"""
Mobile Preview Service for BharatBuild

Generates QR codes for React Native/Expo projects to enable mobile testing
via Expo Go app on physical devices.
"""

import base64
import io
import re
from typing import Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_L
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    logger.warning("qrcode library not available. Mobile preview QR codes will be disabled.")


@dataclass
class ExpoQRResult:
    """Result of QR code generation for Expo"""
    qr_base64: str
    expo_url: str
    qr_type: str  # "tunnel" or "lan"


def parse_expo_url(output: str) -> Optional[Tuple[str, str]]:
    """
    Parse Expo URL from CLI output.

    Returns tuple of (url, type) where type is 'tunnel' or 'lan',
    or None if no URL found.
    """
    # Patterns to detect Expo URLs in order of preference
    patterns = [
        # Expo tunnel URL (works over internet - preferred)
        (r'(exp://u\.expo\.dev/[^\s\x1b]+)', 'tunnel'),
        # Alternative tunnel format
        (r'(exp://[a-z0-9-]+\.exp\.direct[^\s\x1b]*)', 'tunnel'),
        # LAN URL (local network only)
        (r'(exp://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+)', 'lan'),
        # Metro waiting message with URL
        (r'Metro waiting on (exp://[^\s\x1b]+)', 'lan'),
        # Expo Go URL format
        (r'(exp\+[a-zA-Z0-9-]+://expo-development-client[^\s\x1b]*)', 'dev-client'),
    ]

    # Strip ANSI escape codes for reliable matching
    clean_output = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\r', '', output)

    for pattern, url_type in patterns:
        match = re.search(pattern, clean_output, re.IGNORECASE)
        if match:
            url = match.group(1).strip()
            logger.info(f"[MobilePreview] Found Expo URL: {url} (type: {url_type})")
            return url, url_type

    return None


def generate_qr_code(data: str, size: int = 256) -> str:
    """
    Generate QR code as base64-encoded PNG.

    Args:
        data: The data to encode in the QR code
        size: The size of the QR code image in pixels

    Returns:
        Base64-encoded PNG image string
    """
    if not QR_AVAILABLE:
        logger.error("[MobilePreview] QR code generation not available - qrcode library not installed")
        return ""

    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=ERROR_CORRECT_L,
            box_size=10,
            border=2
        )
        qr.add_data(data)
        qr.make(fit=True)

        # Create image with white background
        img = qr.make_image(fill_color="black", back_color="white")

        # Resize to requested size
        img = img.resize((size, size))

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        base64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')

        logger.info(f"[MobilePreview] Generated QR code for: {data[:50]}...")
        return base64_str

    except Exception as e:
        logger.error(f"[MobilePreview] Error generating QR code: {e}")
        return ""


def detect_expo_ready(output: str) -> bool:
    """
    Check if Expo Metro bundler is ready to accept connections.

    Args:
        output: Log output line to check

    Returns:
        True if Expo appears ready
    """
    # Strip ANSI escape codes
    clean_output = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\r', '', output)

    ready_patterns = [
        r'Metro waiting on',
        r'Scan the QR code',
        r'Development mode',
        r'Starting Metro Bundler',
        r'Metro Bundler ready',
        r'Tunnel ready',
        r'Logs for your project',
        r'Open this link',
        r'exp://.*ready',
    ]

    for pattern in ready_patterns:
        if re.search(pattern, clean_output, re.IGNORECASE):
            logger.info(f"[MobilePreview] Expo ready detected: {pattern}")
            return True

    return False


def detect_expo_error(output: str) -> Optional[str]:
    """
    Detect Expo-specific errors in output.

    Args:
        output: Log output line to check

    Returns:
        Error message if error detected, None otherwise
    """
    # Strip ANSI escape codes
    clean_output = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\r', '', output)

    error_patterns = [
        (r'Tunnel URL not found', 'Tunnel connection failed - try again or use LAN mode'),
        (r'ngrok.*error', 'Tunnel service error - network may be restricted'),
        (r'Failed to resolve', 'Failed to resolve Expo URL'),
        (r'Metro.*error', 'Metro bundler error'),
        (r'Unable to find expo', 'Expo not installed correctly'),
        (r'expo.*not found', 'Expo CLI not found'),
    ]

    for pattern, message in error_patterns:
        if re.search(pattern, clean_output, re.IGNORECASE):
            logger.warning(f"[MobilePreview] Expo error detected: {message}")
            return message

    return None


def create_expo_qr_result(output: str, size: int = 256) -> Optional[ExpoQRResult]:
    """
    Create ExpoQRResult from CLI output if possible.

    Convenience function that combines URL parsing and QR generation.

    Args:
        output: CLI output containing Expo URL
        size: QR code size in pixels

    Returns:
        ExpoQRResult if URL found and QR generated, None otherwise
    """
    result = parse_expo_url(output)
    if not result:
        return None

    url, url_type = result
    qr_base64 = generate_qr_code(url, size)

    if not qr_base64:
        return None

    return ExpoQRResult(
        qr_base64=qr_base64,
        expo_url=url,
        qr_type=url_type
    )

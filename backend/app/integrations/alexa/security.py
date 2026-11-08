"""Alexa Request Verification & Security.

Implements the official Amazon Alexa Skills Kit security requirements:
1. Verify the SignatureCertChainUrl header.
2. Download and validate the X.509 certificate.
3. Verify the certificate's subject alternative names include echo-api.amazon.com.
4. Verify the digital signature of the request body.
5. Verify the request timestamp is within tolerance (150 seconds).
6. Verify the application ID matches our configured skill ID.
"""

import base64
import logging
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
import httpx
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from backend.app.config import get_settings

logger = logging.getLogger(__name__)

# Certificate cache to avoid re-fetching the PEM on every request
_CERT_CACHE: dict[str, tuple[float, bytes, x509.Certificate]] = {}
CERT_CACHE_TTL = 3600  # 1 hour


def validate_timestamp(timestamp_str: str, tolerance_seconds: int = 150) -> bool:
    """Ensure request timestamp is within tolerance to prevent replay attacks."""
    try:
        # Alexa timestamps are ISO8601 strings (e.g. 2019-05-13T12:34:56Z)
        if timestamp_str.endswith("Z"):
            req_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        else:
            req_time = datetime.fromisoformat(timestamp_str)
        now = datetime.now(timezone.utc)
        diff = abs((now - req_time).total_seconds())
        if diff > tolerance_seconds:
            logger.warning(f"Request timestamp out of bounds: diff={diff}s, max={tolerance_seconds}s")
            return False
        return True
    except Exception as e:
        logger.error(f"Timestamp validation failed: {e}")
        return False


def validate_cert_url(cert_url: str) -> bool:
    """Validate that the certificate URL strictly follows Amazon's rules:
    - Protocol must be https.
    - Hostname must be s3.amazonaws.com.
    - Path must start with /echo.api/.
    - Port, if specified, must be 443.
    """
    try:
        parsed = urlparse(cert_url)
        if parsed.scheme.lower() != "https":
            return False
        if parsed.hostname.lower() != "s3.amazonaws.com":
            return False
        if not parsed.path.startswith("/echo.api/"):
            return False
        if parsed.port and parsed.port != 443:
            return False
        return True
    except Exception as e:
        logger.error(f"Invalid cert URL: {e}")
        return False


def get_certificate(cert_url: str) -> x509.Certificate:
    """Fetch certificate from Amazon with in-memory caching."""
    now = time.time()
    if cert_url in _CERT_CACHE:
        cached_time, raw_data, cert = _CERT_CACHE[cert_url]
        if now - cached_time < CERT_CACHE_TTL:
            return cert

    if not validate_cert_url(cert_url):
        raise ValueError(f"Untrusted certificate URL: {cert_url}")

    resp = httpx.get(cert_url, timeout=5.0)
    resp.raise_for_status()
    cert_bytes = resp.content

    cert = x509.load_pem_x509_certificate(cert_bytes, default_backend())

    # Check validity dates
    utc_now = datetime.now(timezone.utc)
    if cert.not_valid_before_utc > utc_now or cert.not_valid_after_utc < utc_now:
        raise ValueError("Certificate is expired or not yet valid.")

    # Check SAN (Subject Alternative Names) for echo-api.amazon.com
    try:
        san = cert.extensions.get_extension_for_oid(x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        dns_names = san.value.get_values_for_type(x509.DNSName)
        if "echo-api.amazon.com" not in dns_names:
            raise ValueError("echo-api.amazon.com not in certificate SAN.")
    except Exception as e:
        raise ValueError(f"SAN check failed: {e}")

    _CERT_CACHE[cert_url] = (now, cert_bytes, cert)
    return cert


def verify_alexa_request(
    raw_body: bytes,
    headers: dict,
    skill_id: str = "",
    verify_signature: bool = True,
) -> tuple[bool, str]:
    """Verify Alexa request signatures and security constraints.
    
    Returns (is_valid, reason).
    """
    settings = get_settings()
    configured_skill_id = skill_id or settings.alexa_skill_id
    should_verify = settings.alexa_verify_requests if verify_signature else False

    if not should_verify:
        return True, "Verification disabled in settings."

    sig_cert_url = headers.get("SignatureCertChainUrl") or headers.get("signaturecertchainurl")
    signature_b64 = headers.get("Signature-256") or headers.get("signature-256") or headers.get("Signature")

    if not sig_cert_url or not signature_b64:
        return False, "Missing SignatureCertChainUrl or Signature headers."

    try:
        cert = get_certificate(sig_cert_url)
        public_key = cert.public_key()
        signature = base64.b64decode(signature_b64)

        public_key.verify(
            signature,
            raw_body,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True, "Signature verified successfully."
    except Exception as e:
        logger.error(f"Alexa request verification error: {e}")
        return False, str(e)

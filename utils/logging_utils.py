"""
Logging utilities to prevent sensitive data leakage.

Provides functions to sanitize error messages, database URLs, and other
potentially sensitive information before logging.
"""

import re
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse


def sanitize_database_url(url: str) -> str:
    """
    Remove password from database URL for safe logging.

    Example:
        postgresql://user:password@host:5432/db
        -> postgresql://user:***@host:5432/db

    Args:
        url: Database connection URL

    Returns:
        Sanitized URL with password replaced by ***
    """
    if not url or '://' not in url:
        return url

    try:
        parsed = urlparse(url)
        if parsed.password:
            # Reconstruct netloc with sanitized password
            netloc = f"{parsed.username}:***@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"

            # Reconstruct URL
            sanitized = urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            return sanitized
    except Exception:
        # If parsing fails, try regex fallback
        return re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', url)

    return url


def sanitize_api_key(key: Optional[str], show_prefix: bool = True) -> str:
    """
    Redact API key for safe logging.

    Args:
        key: API key to sanitize
        show_prefix: If True, show first 4 characters (default: True)

    Returns:
        Sanitized key like "sk_t..." or "***"
    """
    if not key:
        return "[not set]"

    if show_prefix and len(key) >= 8:
        return f"{key[:4]}...{key[-4:]}"
    else:
        return "***"


def sanitize_exception(exc: Exception, exc_info: bool = False) -> str:
    """
    Sanitize exception message to remove sensitive data.

    Common patterns removed:
    - Database connection strings with passwords
    - API keys in headers or URLs
    - Session tokens
    - Environment variable values

    Args:
        exc: Exception object
        exc_info: If True, return full sanitized traceback (default: False)

    Returns:
        Sanitized error message
    """
    error_str = str(exc)

    # Sanitize database URLs
    error_str = re.sub(
        r'postgresql://[^:]+:[^@]+@',
        'postgresql://user:***@',
        error_str
    )
    error_str = re.sub(
        r'mysql://[^:]+:[^@]+@',
        'mysql://user:***@',
        error_str
    )

    # Sanitize API keys in headers or params
    error_str = re.sub(
        r'(["\']?x-api-key["\']?\s*[:=]\s*["\']?)([^"\'&\s]+)',
        r'\1***',
        error_str,
        flags=re.IGNORECASE
    )
    error_str = re.sub(
        r'(["\']?api[_-]?key["\']?\s*[:=]\s*["\']?)([^"\'&\s]+)',
        r'\1***',
        error_str,
        flags=re.IGNORECASE
    )

    # Sanitize tokens
    error_str = re.sub(
        r'(["\']?token["\']?\s*[:=]\s*["\']?)([^"\'&\s]+)',
        r'\1***',
        error_str,
        flags=re.IGNORECASE
    )
    error_str = re.sub(
        r'(["\']?session[_-]?id["\']?\s*[:=]\s*["\']?)([^"\'&\s]+)',
        r'\1***',
        error_str,
        flags=re.IGNORECASE
    )

    # Sanitize password parameters
    error_str = re.sub(
        r'(["\']?password["\']?\s*[:=]\s*["\']?)([^"\'&\s]+)',
        r'\1***',
        error_str,
        flags=re.IGNORECASE
    )

    # Sanitize Authorization headers
    error_str = re.sub(
        r'(["\']?authorization["\']?\s*[:=]\s*["\']?)(Bearer\s+)?([^"\'&\s]+)',
        r'\1\2***',
        error_str,
        flags=re.IGNORECASE
    )

    return error_str


def sanitize_url(url: str) -> str:
    """
    Sanitize URL by removing sensitive query parameters and credentials.

    Args:
        url: URL to sanitize

    Returns:
        Sanitized URL
    """
    if not url:
        return url

    try:
        parsed = urlparse(url)

        # Remove username/password from netloc
        netloc = parsed.hostname or ''
        if parsed.port:
            netloc += f":{parsed.port}"

        # Sanitize query string (remove common sensitive params)
        query = parsed.query
        if query:
            # Remove sensitive query parameters
            query = re.sub(
                r'([?&])(api[_-]?key|token|password|secret|auth)=[^&]*',
                r'\1\2=***',
                query,
                flags=re.IGNORECASE
            )

        # Reconstruct URL
        sanitized = urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            query,
            ''  # Remove fragment
        ))
        return sanitized
    except Exception:
        # If parsing fails, return generic placeholder
        return "[url-redacted]"


def safe_log_dict(data: dict, keys_to_redact: Optional[list] = None) -> dict:
    """
    Create a safe copy of dictionary for logging, redacting sensitive keys.

    Args:
        data: Dictionary to sanitize
        keys_to_redact: Additional keys to redact (default: common sensitive keys)

    Returns:
        Sanitized copy of dictionary
    """
    default_redact_keys = {
        'password', 'passwd', 'pwd',
        'api_key', 'apikey', 'api-key',
        'token', 'access_token', 'refresh_token',
        'secret', 'secret_key',
        'session_id', 'sessionid',
        'authorization', 'auth',
        'x-api-key', 'x_api_key'
    }

    if keys_to_redact:
        default_redact_keys.update(k.lower() for k in keys_to_redact)

    safe_dict = {}
    for key, value in data.items():
        if key.lower() in default_redact_keys:
            safe_dict[key] = '***'
        elif isinstance(value, dict):
            safe_dict[key] = safe_log_dict(value, keys_to_redact)
        elif isinstance(value, str) and ('://' in value or '@' in value):
            # Might be a URL or connection string
            safe_dict[key] = sanitize_url(value) if '://' in value else sanitize_database_url(value)
        else:
            safe_dict[key] = value

    return safe_dict


# Example usage:
"""
import logging
from utils.logging_utils import sanitize_exception, sanitize_database_url

logger = logging.getLogger(__name__)

try:
    # Some operation that might fail
    await db.connect("postgresql://user:secret@localhost/db")
except Exception as e:
    # Safe logging - password will be redacted
    logger.error(f"Database connection failed: {sanitize_exception(e)}")
"""

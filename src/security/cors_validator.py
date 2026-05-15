"""CORS origin validation."""
import re
from typing import List
from urllib.parse import urlparse


class CORSValidator:
    """Validates CORS origins."""

    # Valid URL pattern
    _URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$',
        re.IGNORECASE
    )

    @classmethod
    def validate_origins(cls, origins: List[str]) -> List[str]:
        """Validate and filter CORS origins.
        
        Args:
            origins: List of origin strings to validate
            
        Returns:
            List of valid origins
            
        Raises:
            ValueError: If any origin is invalid
        """
        if not origins:
            return []

        valid_origins = []
        invalid_origins = []

        for origin in origins:
            if origin == "*":
                # Wildcard is technically valid but should be explicit
                valid_origins.append(origin)
                continue

            if not cls._is_valid_origin(origin):
                invalid_origins.append(origin)
            else:
                valid_origins.append(origin)

        if invalid_origins:
            raise ValueError(
                f"Invalid CORS origins: {', '.join(invalid_origins)}. "
                "Origins must be valid HTTP/HTTPS URLs."
            )

        return valid_origins

    @classmethod
    def _is_valid_origin(cls, origin: str) -> bool:
        """Check if origin is a valid HTTP/HTTPS URL.
        
        Args:
            origin: Origin string to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not origin:
            return False

        # Check for dangerous protocols
        dangerous_protocols = ["javascript:", "data:", "file:", "vbscript:"]
        if any(origin.lower().startswith(proto) for proto in dangerous_protocols):
            return False

        # Must start with http:// or https://
        if not origin.startswith(("http://", "https://")):
            return False

        # Validate URL structure
        try:
            parsed = urlparse(origin)
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Scheme must be http or https
            if parsed.scheme not in ("http", "https"):
                return False
            
            return True
        except Exception:
            return False

    @classmethod
    def should_allow_credentials(cls, origins: List[str]) -> bool:
        """Determine if credentials should be allowed based on origins.
        
        Credentials cannot be used with wildcard origin per CORS spec.
        
        Args:
            origins: List of CORS origins
            
        Returns:
            True if credentials should be allowed, False otherwise
        """
        return bool(origins) and "*" not in origins

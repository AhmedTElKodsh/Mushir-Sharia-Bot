"""Input validation and sanitization."""
import re
from typing import Optional, Tuple


# Prompt injection patterns
PROMPT_INJECTION_PATTERNS = [
    r'ignore\s+(?:all\s+)?(?:above\s+|previous\s+)?instructions?',
    r'disregard\s+(?:(?:all|the)\s+)?(?:above|previous|prior)\s+instructions?',
    r'forget\s+(previous|all|above)\s+instructions?',
    r'you\s+are\s+now\s+a',
    r'act\s+as\s+(a|an)\s+\w+',
    r'pretend\s+to\s+be',
    r'system\s*:\s*',
    r'<\s*system\s*>',
    r'\[SYSTEM\]',
    r'sudo\s+mode',
    r'developer\s+mode',
    r'admin\s+mode',
    r'jailbreak',
    r'DAN(\s+mode)?',
]

# Compile patterns for performance
_INJECTION_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in PROMPT_INJECTION_PATTERNS]


class InputValidator:
    """Validates and sanitizes user input."""

    def __init__(
        self,
        max_length: int = 2000,
        enable_injection_filter: bool = True,
    ):
        """Initialize input validator.
        
        Args:
            max_length: Maximum allowed query length
            enable_injection_filter: Whether to check for prompt injection
        """
        self.max_length = max_length
        self.enable_injection_filter = enable_injection_filter

    def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """Validate user query.
        
        Args:
            query: User query to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not query or not query.strip():
            return False, "Query cannot be empty"

        if len(query) > self.max_length:
            return False, f"Query exceeds maximum length of {self.max_length} characters"

        if self.enable_injection_filter:
            is_safe, injection_type = self._check_prompt_injection(query)
            if not is_safe:
                return False, f"Query contains potentially harmful content: {injection_type}"

        return True, None

    def _check_prompt_injection(self, query: str) -> Tuple[bool, Optional[str]]:
        """Check for prompt injection attempts.
        
        Args:
            query: Query to check
            
        Returns:
            Tuple of (is_safe, injection_type)
        """
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(query):
                return False, "prompt injection attempt"

        # Check for excessive special characters (potential obfuscation)
        special_char_ratio = sum(1 for c in query if not c.isalnum() and not c.isspace()) / max(len(query), 1)
        if special_char_ratio > 0.4:
            return False, "excessive special characters"

        # Check for repeated instruction-like phrases
        instruction_words = ["must", "should", "need to", "have to", "required to"]
        instruction_count = sum(1 for word in instruction_words if word in query.lower())
        if instruction_count > 5:
            return False, "excessive instruction-like language"

        return True, None

    @staticmethod
    def sanitize_for_logging(query: str, max_length: int = 200) -> str:
        """Sanitize query for safe logging (truncate and remove sensitive patterns).
        
        Args:
            query: Query to sanitize
            max_length: Maximum length for logged query
            
        Returns:
            Sanitized query string
        """
        # Truncate
        sanitized = query[:max_length]
        
        # Add ellipsis if truncated
        if len(query) > max_length:
            sanitized += "..."
        
        return sanitized

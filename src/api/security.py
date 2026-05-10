import re
from typing import Optional
import bleach
from src.config.logging_config import setup_logging

logger = setup_logging()

MAX_INPUT_LENGTH = 5000

def sanitize_user_input(text: str) -> str:
    """Remove dangerous content from user input."""
    if not text:
        return ""
    text = text[:MAX_INPUT_LENGTH]
    text = bleach.clean(text, tags=[], attributes={}, strip=True)
    return text.strip()

def detect_prompt_injection(text: str) -> Optional[str]:
    """Detect potential prompt injection attempts."""
    patterns = [
        r"ignore (all|previous|above) instructions",
        r"you are now (a|an)",
        r"act as (a|an|if you were)",
        r"forget (your|all) (instructions|rules|constraints)",
        r"system prompt",
        r"<\|im_start\|>",
        r"### (instruction|system|user):",
    ]
    text_lower = text.lower()
    for pattern in patterns:
        if re.search(pattern, text_lower):
            logger.warning(f"Potential prompt injection detected: {pattern}")
            return f"Instruction override pattern detected: {pattern}"
    return None

def validate_input(text: str) -> tuple:
    """Validate and sanitize input. Returns (is_valid, sanitized, error)."""
    if not text or not text.strip():
        return False, "", "Input cannot be empty"
    if len(text) > MAX_INPUT_LENGTH:
        return False, "", f"Input exceeds {MAX_INPUT_LENGTH} characters"
    injection = detect_prompt_injection(text)
    if injection:
        return False, "", f"Injection attempt detected: {injection}"
    sanitized = sanitize_user_input(text)
    return True, sanitized, ""

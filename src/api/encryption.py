from cryptography.fernet import Fernet
from typing import Optional
import os
from src.config.logging_config import setup_logging

logger = setup_logging()

class EncryptionService:
    """AES-256 encryption for sensitive data."""

    def __init__(self, key: Optional[str] = None):
        key = key or os.getenv("ENCRYPTION_MASTER_KEY")
        if not key:
            raise ValueError("ENCRYPTION_MASTER_KEY not set")
        self.fernet = Fernet(key.encode() if isinstance(key, str) and len(key) == 44 else Fernet.generate_key())

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext."""
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext."""
        return self.fernet.decrypt(ciphertext.encode()).decode()

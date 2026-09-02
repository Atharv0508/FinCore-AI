from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings


class CredentialCipher:
    """Encrypts third-party credentials before they are stored in MongoDB."""

    def __init__(self, settings: Settings) -> None:
        try:
            self._fernet = Fernet(settings.fernet_key.encode())
        except (TypeError, ValueError) as error:
            raise RuntimeError("FERNET_KEY must be a valid URL-safe base64 Fernet key.") from error

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as error:
            raise RuntimeError("Stored Razorpay credentials cannot be decrypted with the configured FERNET_KEY.") from error

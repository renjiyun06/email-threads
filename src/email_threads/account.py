"""Email account configuration module."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class EmailAccount:
    """
    Email account configuration.

    This class holds the credentials and server information
    for an email account. Both IMAP (for receiving) and SMTP
    (for sending) configurations are supported.

    Attributes:
        email: Email address (e.g., "user@example.com")
        password: Account password or app-specific password
        imap_server: IMAP server hostname (e.g., "imap.gmail.com")
        imap_port: IMAP server port (default: 993 for SSL)
        smtp_server: SMTP server hostname (optional, for sending)
        smtp_port: SMTP server port (default: 465 for SSL)
        imap_ssl: Use SSL for IMAP connection (default: True)
        smtp_ssl: Use SSL for SMTP connection (default: True)
    """

    email: str
    password: str
    imap_server: str
    imap_port: int = 993
    smtp_server: Optional[str] = None
    smtp_port: int = 465
    imap_ssl: bool = True
    smtp_ssl: bool = True

    def __post_init__(self):
        """Validate account configuration after initialization."""
        if not self.email or "@" not in self.email:
            raise ValueError(f"Invalid email address: {self.email}")

        if not self.password:
            raise ValueError("Password cannot be empty")

        if not self.imap_server:
            raise ValueError("IMAP server cannot be empty")

    def has_smtp_config(self) -> bool:
        """
        Check if SMTP configuration is available.

        Returns:
            True if smtp_server is configured, False otherwise
        """
        return self.smtp_server is not None and len(self.smtp_server) > 0

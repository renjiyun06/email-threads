"""Email message data structure module."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class EmailMessage:
    """
    Email message data structure.

    This class encapsulates all relevant information from an email
    message, including headers, content, and metadata needed for
    building reply chains.

    Attributes:
        message_id: Unique message identifier (Message-ID header)
        from_: Sender email address
        to: List of recipient email addresses
        subject: Email subject line
        text: Plain text content of the email
        html: HTML content of the email (optional)
        date: Email timestamp
        in_reply_to: Message-ID of the email being replied to (optional)
        references: List of Message-IDs in the conversation thread
        cc: List of CC recipients (optional)
        bcc: List of BCC recipients (optional)
        raw_headers: Dictionary of raw email headers (optional)
    """

    message_id: str
    from_: str
    to: list[str]
    subject: str
    text: str
    date: datetime
    html: Optional[str] = None
    in_reply_to: Optional[str] = None
    references: list[str] = field(default_factory=list)
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    raw_headers: Optional[dict] = None

    def __post_init__(self):
        """Validate message data after initialization."""
        if not self.message_id:
            raise ValueError("message_id cannot be empty")

        if not self.from_:
            raise ValueError("from_ cannot be empty")

        if not self.to:
            raise ValueError("to cannot be empty")

    def is_reply(self) -> bool:
        """
        Check if this message is a reply to another message.

        Returns:
            True if in_reply_to is set, False otherwise
        """
        return self.in_reply_to is not None

    def get_all_recipients(self) -> list[str]:
        """
        Get all recipients (to + cc + bcc).

        Returns:
            Combined list of all recipient email addresses
        """
        return self.to + self.cc + self.bcc

    def __repr__(self) -> str:
        """
        String representation for debugging.

        Returns:
            Formatted string with key message information
        """
        return (
            f"EmailMessage(message_id='{self.message_id[:20]}...', "
            f"from_='{self.from_}', subject='{self.subject[:30]}...', "
            f"date={self.date})"
        )

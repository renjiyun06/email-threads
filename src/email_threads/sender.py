"""Email sending module using SMTP."""

import logging
import smtplib
import ssl
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from .account import EmailAccount
from .message import EmailMessage

logger = logging.getLogger(__name__)


class EmailSender:
    """
    Email sender using SMTP protocol.

    This class handles sending emails through SMTP, including
    proper handling of reply headers (In-Reply-To, References)
    for maintaining conversation threads.
    """

    def __init__(self, account: EmailAccount):
        """
        Initialize email sender with an account.

        Args:
            account: EmailAccount with SMTP configuration

        Raises:
            ValueError: If account doesn't have SMTP configuration
        """
        if not account.has_smtp_config():
            raise ValueError(
                f"Account {account.email} does not have SMTP "
                f"configuration"
            )

        self.account = account
        logger.info(f"EmailSender initialized for {account.email}")

    def send(
        self,
        to: str,
        subject: str,
        text: str,
        html: Optional[str] = None,
        reply_to_message: Optional[EmailMessage] = None,
        cc: Optional[list[str]] = None,
        bcc: Optional[list[str]] = None,
    ) -> str:
        """
        Send an email.

        Args:
            to: Recipient email address
            subject: Email subject
            text: Plain text content
            html: HTML content (optional)
            reply_to_message: If this is a reply, the original message
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)

        Returns:
            Generated Message-ID for the sent email

        Raises:
            smtplib.SMTPException: If sending fails
        """
        logger.info(
            f"Sending email from {self.account.email} to {to}: "
            f"{subject[:50]}..."
        )

        # Create message
        msg = MIMEMultipart("alternative")
        msg["From"] = self.account.email
        msg["To"] = to
        msg["Subject"] = subject

        # Generate unique Message-ID
        message_id = self._generate_message_id()
        msg["Message-ID"] = message_id
        logger.debug(f"Generated Message-ID: {message_id}")

        # Add CC and BCC if provided
        if cc:
            msg["Cc"] = ", ".join(cc)
        if bcc:
            msg["Bcc"] = ", ".join(bcc)

        # Handle reply headers
        if reply_to_message:
            logger.debug(
                f"Setting up reply headers for "
                f"{reply_to_message.message_id[:30]}..."
            )
            self._add_reply_headers(msg, reply_to_message)

        # Attach text content
        text_part = MIMEText(text, "plain", "utf-8")
        msg.attach(text_part)

        # Attach HTML content if provided
        if html:
            html_part = MIMEText(html, "html", "utf-8")
            msg.attach(html_part)

        # Send via SMTP
        try:
            self._send_via_smtp(msg, to, cc, bcc)
            logger.info(f"Email sent successfully: {message_id}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            raise

        return message_id

    def _generate_message_id(self) -> str:
        """
        Generate a unique Message-ID.

        Returns:
            Message-ID string in standard format
        """
        # Extract domain from email address
        domain = self.account.email.split("@")[1]

        # Generate unique ID
        unique_id = str(uuid.uuid4())

        # Format: <unique_id@domain>
        return f"<{unique_id}@{domain}>"

    def _add_reply_headers(
        self,
        msg: MIMEMultipart,
        reply_to_message: EmailMessage
    ) -> None:
        """
        Add reply headers to maintain conversation thread.

        Args:
            msg: The message to add headers to
            reply_to_message: The message being replied to
        """
        # Set In-Reply-To
        msg["In-Reply-To"] = reply_to_message.message_id
        logger.debug(f"Set In-Reply-To: {reply_to_message.message_id[:30]}...")

        # Build References header
        references = []

        # Include existing references from parent
        if reply_to_message.references:
            references.extend(reply_to_message.references)

        # Add parent's Message-ID
        if reply_to_message.message_id not in references:
            references.append(reply_to_message.message_id)

        # Set References header
        if references:
            msg["References"] = " ".join(references)
            logger.debug(
                f"Set References with {len(references)} message(s)"
            )

    def _send_via_smtp(
        self,
        msg: MIMEMultipart,
        to: str,
        cc: Optional[list[str]],
        bcc: Optional[list[str]]
    ) -> None:
        """
        Send message via SMTP server.

        Args:
            msg: Prepared MIME message
            to: Primary recipient
            cc: CC recipients
            bcc: BCC recipients

        Raises:
            smtplib.SMTPException: If connection or sending fails
        """
        # Collect all recipients
        all_recipients = [to]
        if cc:
            all_recipients.extend(cc)
        if bcc:
            all_recipients.extend(bcc)

        logger.debug(
            f"Connecting to SMTP server: "
            f"{self.account.smtp_server}:{self.account.smtp_port}"
        )

        # Create SSL context (less strict for compatibility)
        context = ssl.create_default_context()
        # Allow older protocols for QQ mail compatibility
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # Connect and send
        if self.account.smtp_ssl:
            # Use SMTP_SSL for port 465
            logger.debug("Using SMTP_SSL")
            server = smtplib.SMTP_SSL(
                self.account.smtp_server,
                self.account.smtp_port,
                context=context
            )
        else:
            # Use SMTP with STARTTLS for port 587
            logger.debug("Using SMTP with STARTTLS")
            server = smtplib.SMTP(
                self.account.smtp_server,
                self.account.smtp_port
            )
            server.starttls(context=context)

        try:
            logger.debug("SMTP connection established")

            # Login
            server.login(self.account.email, self.account.password)
            logger.debug("SMTP authentication successful")

            # Send email
            server.send_message(msg, to_addrs=all_recipients)
            logger.debug(
                f"Email sent to {len(all_recipients)} recipient(s)"
            )
        finally:
            server.quit()
            logger.debug("SMTP connection closed")

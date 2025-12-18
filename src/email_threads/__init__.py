"""
email-threads: Multi-account email monitoring with reply chain support.

This library provides a simple way to monitor multiple email accounts
simultaneously and build complete conversation threads. It's designed
for applications that need to track email conversations, such as
AI agents, customer service systems, or team collaboration tools.

Key Features:
    - Multi-account monitoring with IMAP IDLE (real-time)
    - Automatic reply chain construction
    - Thread-safe message storage
    - Simple callback-based API

Basic Usage:
    >>> from email_threads import (
    ...     EmailThreadsMonitor,
    ...     EmailAccount,
    ...     EmailSender
    ... )
    >>>
    >>> # Configure accounts
    >>> accounts = [
    ...     EmailAccount(
    ...         email="account1@example.com",
    ...         password="password1",
    ...         imap_server="imap.example.com",
    ...         smtp_server="smtp.example.com"
    ...     ),
    ...     EmailAccount(
    ...         email="account2@example.com",
    ...         password="password2",
    ...         imap_server="imap.example.com"
    ...     )
    ... ]
    >>>
    >>> # Define message handler
    >>> def handle_message(message, thread):
    ...     print(f"New message: {message.subject}")
    ...     print(f"Thread length: {len(thread)}")
    >>>
    >>> # Start monitoring
    >>> monitor = EmailThreadsMonitor(accounts, handle_message)
    >>> monitor.start()  # Blocking

For more information, see the documentation at:
https://github.com/yourusername/email-threads
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__license__ = "MIT"

# Public API exports
from .account import EmailAccount
from .message import EmailMessage
from .monitor import EmailThreadsMonitor
from .sender import EmailSender
from .storage import MessageStorage
from .reply_chain import ReplyChainBuilder

__all__ = [
    "EmailAccount",
    "EmailMessage",
    "EmailThreadsMonitor",
    "EmailSender",
    "MessageStorage",
    "ReplyChainBuilder",
]

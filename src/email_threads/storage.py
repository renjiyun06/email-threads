"""In-memory message storage module."""

import logging
from threading import Lock
from typing import Optional

from .message import EmailMessage

logger = logging.getLogger(__name__)


class MessageStorage:
    """
    Thread-safe in-memory storage for email messages.

    This class provides a simple key-value store for caching email
    messages by their Message-ID. It uses threading locks to ensure
    thread-safety when accessed from multiple monitoring threads.

    The storage only keeps messages that are relevant to the monitored
    accounts (i.e., messages exchanged between monitored accounts).
    """

    def __init__(self):
        """Initialize an empty message storage."""
        self._messages: dict[str, EmailMessage] = {}
        self._lock = Lock()
        logger.debug("MessageStorage initialized")

    def add(self, message: EmailMessage) -> None:
        """
        Add a message to storage.

        If a message with the same Message-ID already exists,
        it will be replaced with the new message.

        Args:
            message: EmailMessage instance to store

        Raises:
            ValueError: If message is None or has empty message_id
        """
        if message is None:
            raise ValueError("Cannot add None message to storage")

        if not message.message_id:
            raise ValueError("Cannot add message with empty message_id")

        with self._lock:
            self._messages[message.message_id] = message
            logger.debug(
                f"Message added to storage: {message.message_id[:30]}... "
                f"(total: {len(self._messages)})"
            )

    def get(self, message_id: str) -> Optional[EmailMessage]:
        """
        Retrieve a message by its Message-ID.

        Args:
            message_id: The Message-ID to lookup

        Returns:
            EmailMessage if found, None otherwise
        """
        if not message_id:
            logger.warning("Attempted to get message with empty message_id")
            return None

        with self._lock:
            message = self._messages.get(message_id)
            if message:
                logger.debug(f"Message found in storage: {message_id[:30]}...")
            else:
                logger.debug(
                    f"Message not found in storage: {message_id[:30]}..."
                )
            return message

    def exists(self, message_id: str) -> bool:
        """
        Check if a message exists in storage.

        Args:
            message_id: The Message-ID to check

        Returns:
            True if message exists, False otherwise
        """
        if not message_id:
            return False

        with self._lock:
            return message_id in self._messages

    def get_all_message_ids(self) -> list[str]:
        """
        Get all Message-IDs currently in storage.

        Returns:
            List of all Message-IDs
        """
        with self._lock:
            return list(self._messages.keys())

    def count(self) -> int:
        """
        Get the total number of messages in storage.

        Returns:
            Number of stored messages
        """
        with self._lock:
            return len(self._messages)

    def clear(self) -> None:
        """
        Remove all messages from storage.

        This is useful for testing or resetting the storage state.
        """
        with self._lock:
            count = len(self._messages)
            self._messages.clear()
            logger.info(f"Storage cleared ({count} messages removed)")

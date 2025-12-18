"""Reply chain building module."""

import logging
from typing import Optional

from .message import EmailMessage
from .storage import MessageStorage

logger = logging.getLogger(__name__)


class ReplyChainBuilder:
    """
    Builder for constructing email reply chains.

    This class recursively traces the In-Reply-To headers to build
    a complete conversation thread. Messages are returned in
    chronological order (oldest to newest).

    If a parent message is not found in storage (e.g., it was sent
    before monitoring started), the chain will still be built with
    the available messages.
    """

    def __init__(self, storage: MessageStorage):
        """
        Initialize the reply chain builder.

        Args:
            storage: MessageStorage instance to lookup messages
        """
        self.storage = storage
        logger.debug("ReplyChainBuilder initialized")

    def build_chain(self, message: EmailMessage) -> list[EmailMessage]:
        """
        Build complete reply chain for a message.

        This method recursively traces back through In-Reply-To
        headers to find all parent messages, then returns them
        in chronological order.

        Args:
            message: The message to build a chain for

        Returns:
            List of EmailMessage objects in chronological order
            (oldest first, current message last)
        """
        if message is None:
            logger.warning("Cannot build chain for None message")
            return []

        logger.debug(
            f"Building reply chain for message: "
            f"{message.message_id[:30]}..."
        )

        # Collect all messages in the chain (newest to oldest)
        chain_reversed = []
        current = message
        visited = set()  # Prevent infinite loops

        while current is not None:
            # Check for circular reference
            if current.message_id in visited:
                logger.warning(
                    f"Circular reference detected in reply chain: "
                    f"{current.message_id[:30]}..."
                )
                break

            visited.add(current.message_id)
            chain_reversed.append(current)

            # Try to find parent message
            if current.in_reply_to:
                parent = self.storage.get(current.in_reply_to)
                if parent:
                    logger.debug(
                        f"Found parent message: "
                        f"{parent.message_id[:30]}..."
                    )
                    current = parent
                else:
                    logger.debug(
                        f"Parent message not found in storage: "
                        f"{current.in_reply_to[:30]}..."
                    )
                    current = None
            else:
                # No parent, this is the root message
                logger.debug("Reached root message (no in_reply_to)")
                current = None

        # Reverse to get chronological order (oldest to newest)
        chain = list(reversed(chain_reversed))

        logger.info(
            f"Reply chain built: {len(chain)} message(s) "
            f"for {message.message_id[:30]}..."
        )

        return chain

    def get_thread_root(self, message: EmailMessage) -> Optional[EmailMessage]:
        """
        Find the root message of a thread.

        The root message is the first message in the conversation
        (the one with no In-Reply-To header).

        Args:
            message: Any message in the thread

        Returns:
            The root EmailMessage, or None if not found
        """
        chain = self.build_chain(message)
        if chain:
            return chain[0]
        return None

    def get_thread_length(self, message: EmailMessage) -> int:
        """
        Get the total number of messages in a thread.

        Args:
            message: Any message in the thread

        Returns:
            Number of messages in the thread
        """
        return len(self.build_chain(message))

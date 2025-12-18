"""Email threads monitoring module."""

import logging
import threading
from typing import Callable, Optional

from imap_tools import MailBox, AND

from .account import EmailAccount
from .message import EmailMessage
from .reply_chain import ReplyChainBuilder
from .storage import MessageStorage

logger = logging.getLogger(__name__)


class EmailThreadsMonitor:
    """
    Multi-account email threads monitor.

    This class monitors multiple email accounts simultaneously using
    IMAP IDLE protocol. It captures all emails exchanged between the
    monitored accounts and builds complete reply chains.

    Key features:
    - Multi-account monitoring with separate threads
    - IMAP IDLE for real-time notifications (1-2 second latency)
    - Automatic reply chain construction
    - Thread-safe message storage
    """

    def __init__(
        self,
        accounts: list[EmailAccount],
        on_message_callback: Callable[[EmailMessage, list[EmailMessage]], None],
        auto_mark_seen: bool = False
    ):
        """
        Initialize the email threads monitor.

        Args:
            accounts: List of EmailAccount objects to monitor
            on_message_callback: Callback function invoked when a new
                                 relevant message is received.
                                 Parameters: (current_message, reply_chain)
            auto_mark_seen: If True, automatically mark processed emails as
                           seen. This significantly improves performance by
                           reducing duplicate fetches, but changes mailbox
                           state. Recommended for dedicated agent accounts.
                           Default: False (conservative, no mailbox changes)

        Raises:
            ValueError: If accounts list is empty
        """
        if not accounts:
            raise ValueError("At least one account must be provided")

        self.accounts = accounts
        self.on_message_callback = on_message_callback
        self.auto_mark_seen = auto_mark_seen

        # Create monitored email addresses set for filtering
        self.monitored_emails = {acc.email for acc in accounts}

        # Initialize storage and reply chain builder
        self.storage = MessageStorage()
        self.chain_builder = ReplyChainBuilder(self.storage)

        # Threading control
        self._stop_event = threading.Event()
        self._monitor_threads: list[threading.Thread] = []

        logger.info(
            f"EmailThreadsMonitor initialized with "
            f"{len(accounts)} account(s)"
        )
        logger.debug(f"Monitored emails: {self.monitored_emails}")

    def start(self) -> None:
        """
        Start monitoring all accounts (blocking).

        This method starts a monitoring thread for each account and
        then blocks until stop() is called. Each thread uses IMAP IDLE
        to receive real-time notifications of new emails.

        Note: This is a blocking call. Use start_async() for
        non-blocking operation.
        """
        logger.info("Starting email monitoring (blocking mode)...")

        # Clear stop event
        self._stop_event.clear()

        # Start monitoring threads for each account
        for account in self.accounts:
            thread = threading.Thread(
                target=self._monitor_account,
                args=(account,),
                daemon=True,
                name=f"Monitor-{account.email}"
            )
            thread.start()
            self._monitor_threads.append(thread)
            logger.info(f"Monitoring thread started for {account.email}")

        logger.info("All monitoring threads started")

        # Block until stop is called
        try:
            self._stop_event.wait()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, stopping...")
            self.stop()

        logger.info("Monitoring stopped")

    def start_async(self) -> None:
        """
        Start monitoring all accounts (non-blocking).

        This method starts monitoring threads and returns immediately.
        Call stop() to stop monitoring.
        """
        logger.info("Starting email monitoring (async mode)...")

        # Clear stop event
        self._stop_event.clear()

        # Start monitoring threads for each account
        for account in self.accounts:
            thread = threading.Thread(
                target=self._monitor_account,
                args=(account,),
                daemon=True,
                name=f"Monitor-{account.email}"
            )
            thread.start()
            self._monitor_threads.append(thread)
            logger.info(
                f"Monitoring thread started for {account.email} (async)"
            )

        logger.info("All monitoring threads started (async)")

    def stop(self) -> None:
        """
        Stop monitoring all accounts.

        This sets the stop event and waits for all monitoring threads
        to terminate gracefully.
        """
        logger.info("Stopping email monitoring...")
        self._stop_event.set()

        # Wait for all threads to finish
        for thread in self._monitor_threads:
            thread.join(timeout=5)
            logger.debug(f"Thread {thread.name} stopped")

        self._monitor_threads.clear()
        logger.info("All monitoring threads stopped")

    def get_storage(self) -> MessageStorage:
        """
        Get the message storage instance.

        Returns:
            MessageStorage instance used by this monitor
        """
        return self.storage

    def get_thread(self, message_id: str) -> list[EmailMessage]:
        """
        Get complete thread for a message by Message-ID.

        Args:
            message_id: Message-ID to lookup

        Returns:
            List of EmailMessage objects in chronological order,
            or empty list if message not found
        """
        message = self.storage.get(message_id)
        if message:
            return self.chain_builder.build_chain(message)
        return []

    def _monitor_account(self, account: EmailAccount) -> None:
        """
        Monitor a single account using IMAP IDLE.

        This method runs in a separate thread and continuously monitors
        the account's inbox for new messages.

        Args:
            account: EmailAccount to monitor
        """
        logger.info(f"[{account.email}] Starting account monitoring")

        while not self._stop_event.is_set():
            try:
                # Connect to IMAP server
                logger.debug(
                    f"[{account.email}] Connecting to IMAP: "
                    f"{account.imap_server}:{account.imap_port}"
                )

                with MailBox(account.imap_server).login(
                    account.email,
                    account.password
                ) as mailbox:
                    logger.info(
                        f"[{account.email}] IMAP connection established"
                    )

                    # Initialize: silently load existing messages to storage
                    # (without triggering callbacks)
                    self._initialize_existing_messages(mailbox, account)

                    # Start IDLE loop
                    self._idle_loop(mailbox, account)

            except Exception as e:
                logger.error(
                    f"[{account.email}] Monitoring error: {e}",
                    exc_info=True
                )

                # Check if we should stop
                if self._stop_event.is_set():
                    break

                # Wait before reconnecting
                logger.info(
                    f"[{account.email}] Waiting 10s before reconnect..."
                )
                self._stop_event.wait(10)

        logger.info(f"[{account.email}] Account monitoring stopped")

    def _idle_loop(self, mailbox: MailBox, account: EmailAccount) -> None:
        """
        IMAP IDLE monitoring loop.

        Args:
            mailbox: Connected MailBox instance
            account: EmailAccount being monitored
        """
        logger.debug(f"[{account.email}] Entering IDLE loop")

        while not self._stop_event.is_set():
            try:
                # Start IDLE and wait for new messages
                logger.debug(f"[{account.email}] Starting IDLE (30s)...")

                responses = mailbox.idle.wait(timeout=30)

                if responses:
                    logger.info(
                        f"[{account.email}] IDLE notification received: "
                        f"{len(responses)} event(s)"
                    )

                    # Fetch and process new messages
                    self._process_new_messages(mailbox, account)
                else:
                    logger.debug(
                        f"[{account.email}] IDLE timeout, restarting..."
                    )

            except Exception as e:
                logger.error(
                    f"[{account.email}] IDLE loop error: {e}",
                    exc_info=True
                )
                break

    def _initialize_existing_messages(
        self,
        mailbox: MailBox,
        account: EmailAccount
    ) -> None:
        """
        Initialize storage with existing unread messages (without callbacks).

        This method is called once when monitoring starts. It silently
        loads all existing unread messages into storage so they won't
        trigger callbacks when IDLE is activated. Only messages that
        arrive AFTER monitoring starts will trigger callbacks.

        Args:
            mailbox: Connected MailBox instance
            account: EmailAccount being initialized
        """
        logger.info(
            f"[{account.email}] Initializing: loading existing messages..."
        )

        try:
            loaded_count = 0
            relevant_count = 0

            # Fetch all existing unseen messages
            for msg in mailbox.fetch(AND(seen=False), mark_seen=False):
                # Get message ID
                msg_id = msg.headers.get("message-id", [""])[0].strip()

                # Skip if already in storage (shouldn't happen on first run)
                if self.storage.exists(msg_id):
                    continue

                # Check if this message is relevant
                if self._is_relevant_message(msg, account):
                    # Convert to EmailMessage
                    email_msg = self._convert_to_email_message(msg)

                    # Store message WITHOUT triggering callback
                    self.storage.add(email_msg)
                    relevant_count += 1

                    logger.debug(
                        f"[{account.email}] Pre-loaded: "
                        f"{email_msg.subject[:40]}..."
                    )

                loaded_count += 1

            logger.info(
                f"[{account.email}] Initialization complete: "
                f"pre-loaded {relevant_count} relevant message(s) "
                f"(out of {loaded_count} total unseen)"
            )

        except Exception as e:
            logger.error(
                f"[{account.email}] Error initializing messages: {e}",
                exc_info=True
            )

    def _process_new_messages(
        self,
        mailbox: MailBox,
        account: EmailAccount
    ) -> None:
        """
        Process new messages in the inbox.

        Args:
            mailbox: Connected MailBox instance
            account: EmailAccount being processed
        """
        logger.debug(f"[{account.email}] Fetching new messages...")

        try:
            fetched_count = 0
            processed_count = 0

            # Fetch unseen messages
            # Use auto_mark_seen setting to reduce duplicate fetches
            for msg in mailbox.fetch(
                AND(seen=False),
                mark_seen=self.auto_mark_seen
            ):
                fetched_count += 1
                logger.debug(
                    f"[{account.email}] Processing message: "
                    f"{msg.subject[:50]}..."
                )

                # Get message ID early for duplicate check
                msg_id = msg.headers.get("message-id", [""])[0].strip()

                # Skip if already processed
                if self.storage.exists(msg_id):
                    logger.debug(
                        f"[{account.email}] Message already processed, "
                        f"skipping: {msg_id[:30]}..."
                    )
                    continue

                # Check if this message is relevant
                if self._is_relevant_message(msg, account):
                    # Convert to EmailMessage
                    email_msg = self._convert_to_email_message(msg)

                    # Store message
                    self.storage.add(email_msg)

                    # Build reply chain
                    reply_chain = self.chain_builder.build_chain(email_msg)

                    # Trigger callback
                    logger.info(
                        f"[{account.email}] Triggering callback for: "
                        f"{email_msg.subject[:50]}..."
                    )

                    try:
                        self.on_message_callback(email_msg, reply_chain)
                        processed_count += 1
                    except Exception as e:
                        logger.error(
                            f"[{account.email}] Callback error: {e}",
                            exc_info=True
                        )
                else:
                    logger.debug(
                        f"[{account.email}] Message not relevant, skipping"
                    )

            # Log summary
            if fetched_count > 0:
                logger.info(
                    f"[{account.email}] Fetch complete: "
                    f"fetched {fetched_count} unseen message(s), "
                    f"processed {processed_count} new message(s)"
                )

        except Exception as e:
            logger.error(
                f"[{account.email}] Error processing messages: {e}",
                exc_info=True
            )

    def _is_relevant_message(self, msg, account: EmailAccount) -> bool:
        """
        Check if a message is relevant for monitoring.

        A message is relevant ONLY if it's communication BETWEEN
        monitored accounts:
        1. It's from a monitored account, AND
        2. It's to (at least one) monitored account

        This ensures we only track emails exchanged between the
        accounts we're monitoring, not external communications.

        Args:
            msg: imap_tools Message object
            account: Account that received this message

        Returns:
            True if message should be processed, False otherwise
        """
        # Check sender
        sender = msg.from_

        # Check recipients (to + cc)
        recipients = set(msg.to)
        if msg.cc:
            recipients.update(msg.cc)

        # Message is relevant ONLY if both sender and recipient
        # are monitored accounts
        from_monitored = sender in self.monitored_emails
        to_monitored = bool(recipients & self.monitored_emails)

        is_relevant = from_monitored and to_monitored

        logger.debug(
            f"[{account.email}] Relevance check: "
            f"from={sender}, to={list(recipients)}, "
            f"from_monitored={from_monitored}, "
            f"to_monitored={to_monitored}, "
            f"relevant={is_relevant}"
        )

        return is_relevant

    def _convert_to_email_message(self, msg) -> EmailMessage:
        """
        Convert imap_tools Message to EmailMessage.

        Args:
            msg: imap_tools Message object

        Returns:
            EmailMessage instance
        """
        # Extract References header
        references = []
        if msg.headers.get("references"):
            refs_str = msg.headers.get("references")[0]
            # Split by whitespace and filter empty strings
            references = [
                ref.strip() for ref in refs_str.split()
                if ref.strip()
            ]

        # Extract In-Reply-To
        in_reply_to = None
        if msg.headers.get("in-reply-to"):
            in_reply_to = msg.headers.get("in-reply-to")[0].strip()

        # Create EmailMessage
        email_msg = EmailMessage(
            message_id=msg.headers.get("message-id", [""])[0].strip(),
            from_=msg.from_,
            to=list(msg.to),
            subject=msg.subject or "",
            text=msg.text or "",
            html=msg.html or None,
            date=msg.date,
            in_reply_to=in_reply_to,
            references=references,
            cc=list(msg.cc) if msg.cc else [],
            bcc=list(msg.bcc) if msg.bcc else [],
            raw_headers=dict(msg.headers)
        )

        logger.debug(
            f"Converted message: {email_msg.message_id[:30]}... "
            f"(has_reply_to={email_msg.is_reply()})"
        )

        return email_msg

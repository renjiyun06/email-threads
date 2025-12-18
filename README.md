# email-threads

Multi-account email monitoring library with automatic reply chain construction.

[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Overview

`email-threads` is a Python library designed to monitor multiple email accounts simultaneously and build complete conversation threads. It's perfect for building email-based AI agents, customer service systems, or any application that needs to track email conversations across multiple accounts.

### Key Features

- **Multi-Account Monitoring**: Monitor multiple email accounts in parallel
- **Real-Time IMAP IDLE**: Receive new emails with 1-2 second latency using IMAP IDLE protocol
- **Reply Chain Construction**: Automatically build complete conversation threads using email headers
- **Thread-Safe Storage**: In-memory message storage with thread safety guarantees
- **SMTP Email Sending**: Send emails with proper reply headers (In-Reply-To, References)
- **Account Equality**: All monitored accounts are treated equally - no distinction between "agent" and "user" accounts
- **Simple Callback API**: Easy integration with custom message handlers

## Installation

### From GitHub

```bash
# Using uv (recommended)
uv add git+https://github.com/renjiyun06/email-threads.git

# Using pip
pip install git+https://github.com/renjiyun06/email-threads.git
```

### Local Development

```bash
# Clone the repository
git clone https://github.com/renjiyun06/email-threads.git
cd email-threads

# Install in editable mode
uv add --editable .
```

## Quick Start

### Basic Monitoring

```python
from email_threads import EmailThreadsMonitor, EmailAccount

# Configure accounts to monitor
accounts = [
    EmailAccount(
        email="account1@example.com",
        password="password1",
        imap_server="imap.example.com",
        smtp_server="smtp.example.com"
    ),
    EmailAccount(
        email="account2@example.com",
        password="password2",
        imap_server="imap.example.com",
        smtp_server="smtp.example.com"
    )
]

# Define message handler
def handle_message(message, thread):
    """Called when a new relevant message is received"""
    print(f"New message: {message.subject}")
    print(f"From: {message.from_}")
    print(f"Thread length: {len(thread)} messages")

# Start monitoring
monitor = EmailThreadsMonitor(accounts, handle_message)
monitor.start()  # Blocking - press Ctrl+C to stop
```

### Sending Emails

```python
from email_threads import EmailSender, EmailAccount

# Create sender
account = EmailAccount(
    email="sender@example.com",
    password="password",
    imap_server="imap.example.com",
    smtp_server="smtp.example.com"
)
sender = EmailSender(account)

# Send a simple email
message_id = sender.send(
    to="recipient@example.com",
    subject="Hello",
    text="This is a test email"
)

# Send a reply (with proper threading headers)
original_message = ...  # EmailMessage object from monitor
sender.send(
    to=original_message.from_,
    subject=f"Re: {original_message.subject}",
    text="This is a reply",
    reply_to_message=original_message
)
```

### Async Integration

The library uses threads internally but can be easily integrated into async applications:

```python
import asyncio
from email_threads import EmailThreadsMonitor, EmailAccount

async def main():
    accounts = [...]  # Your accounts

    def handle_message(message, thread):
        # Bridge to async handler
        asyncio.create_task(async_handler(message, thread))

    monitor = EmailThreadsMonitor(accounts, handle_message)
    monitor.start_async()  # Non-blocking

    # Your async code continues
    await asyncio.sleep(3600)

    monitor.stop()

asyncio.run(main())
```

## Core Concepts

### Account Equality

Unlike some email libraries that distinguish between "agent" and "user" accounts, `email-threads` treats all accounts equally. The library monitors all configured accounts and captures emails exchanged **between** these accounts.

This design is ideal for:
- AI agents managing one account while monitoring user accounts
- Team collaboration tools monitoring multiple team members
- Customer service systems tracking conversations across departments

### Reply Chain Construction

The library automatically builds conversation threads by:

1. Tracking `Message-ID`, `In-Reply-To`, and `References` headers
2. Recursively tracing parent messages
3. Storing messages in chronological order (oldest to newest)
4. Handling missing messages gracefully

### Memory Storage

Messages are stored in memory during the monitoring session:
- **Only relevant messages** are stored (between monitored accounts)
- **Only new messages** are stored (since monitoring started)
- Storage is **thread-safe** for concurrent access
- **No persistence** - data is lost when the program stops

This approach ensures:
- Fast startup (no loading historical emails)
- Controlled memory usage (only monitored conversations)
- O(1) message lookup by Message-ID

## API Reference

### EmailAccount

Configuration for an email account.

```python
EmailAccount(
    email: str,                    # Email address
    password: str,                 # Password or app-specific password
    imap_server: str,              # IMAP server hostname
    imap_port: int = 993,          # IMAP port (default: 993)
    smtp_server: str = None,       # SMTP server (optional)
    smtp_port: int = 465,          # SMTP port (default: 465)
    imap_ssl: bool = True,         # Use SSL for IMAP
    smtp_ssl: bool = True          # Use SSL for SMTP
)
```

### EmailMessage

Data structure representing an email message.

**Attributes:**
- `message_id: str` - Unique message identifier
- `from_: str` - Sender email address
- `to: list[str]` - List of recipients
- `subject: str` - Email subject
- `text: str` - Plain text content
- `html: str` - HTML content (optional)
- `date: datetime` - Email timestamp
- `in_reply_to: str` - Parent message ID (optional)
- `references: list[str]` - List of referenced message IDs
- `cc: list[str]` - CC recipients
- `bcc: list[str]` - BCC recipients

**Methods:**
- `is_reply() -> bool` - Check if this is a reply
- `get_all_recipients() -> list[str]` - Get all recipients (to + cc + bcc)

### EmailThreadsMonitor

Multi-account email monitor.

```python
EmailThreadsMonitor(
    accounts: list[EmailAccount],
    on_message_callback: Callable[[EmailMessage, list[EmailMessage]], None]
)
```

**Methods:**
- `start()` - Start monitoring (blocking)
- `start_async()` - Start monitoring (non-blocking)
- `stop()` - Stop monitoring
- `get_storage() -> MessageStorage` - Access message storage
- `get_thread(message_id: str) -> list[EmailMessage]` - Get thread for a message

### EmailSender

SMTP email sender.

```python
EmailSender(account: EmailAccount)
```

**Methods:**
```python
send(
    to: str,
    subject: str,
    text: str,
    html: str = None,
    reply_to_message: EmailMessage = None,
    cc: list[str] = None,
    bcc: list[str] = None
) -> str  # Returns Message-ID
```

### MessageStorage

Thread-safe in-memory message storage.

**Methods:**
- `add(message: EmailMessage)` - Store a message
- `get(message_id: str) -> EmailMessage` - Retrieve by Message-ID
- `exists(message_id: str) -> bool` - Check if message exists
- `count() -> int` - Get total message count
- `clear()` - Remove all messages

### ReplyChainBuilder

Build conversation threads from messages.

```python
ReplyChainBuilder(storage: MessageStorage)
```

**Methods:**
- `build_chain(message: EmailMessage) -> list[EmailMessage]` - Build thread
- `get_thread_root(message: EmailMessage) -> EmailMessage` - Find root message
- `get_thread_length(message: EmailMessage) -> int` - Count messages in thread

## Configuration Examples

### Gmail

```python
EmailAccount(
    email="user@gmail.com",
    password="app_specific_password",  # Generate at Google Account settings
    imap_server="imap.gmail.com",
    smtp_server="smtp.gmail.com"
)
```

### QQ Mail

```python
EmailAccount(
    email="user@qq.com",
    password="authorization_code",  # Not login password
    imap_server="imap.qq.com",
    smtp_server="smtp.qq.com"
)
```

### Outlook

```python
EmailAccount(
    email="user@outlook.com",
    password="password",
    imap_server="outlook.office365.com",
    smtp_server="smtp.office365.com"
)
```

## Use Cases

### Email-Based AI Agent

```python
from email_threads import EmailThreadsMonitor, EmailAccount, EmailSender

# Monitor agent's account and user accounts
agent_account = EmailAccount(...)
user_accounts = [EmailAccount(...), EmailAccount(...)]
all_accounts = [agent_account] + user_accounts

# Create sender for agent
agent_sender = EmailSender(agent_account)

def handle_message(message, thread):
    # Only respond to messages sent TO the agent
    if agent_account.email in message.to:
        # Generate AI response based on conversation thread
        response = generate_ai_response(thread)

        # Send reply
        agent_sender.send(
            to=message.from_,
            subject=f"Re: {message.subject}",
            text=response,
            reply_to_message=message
        )

monitor = EmailThreadsMonitor(all_accounts, handle_message)
monitor.start()
```

### Team Collaboration Tracker

```python
team_accounts = [
    EmailAccount(email="alice@team.com", ...),
    EmailAccount(email="bob@team.com", ...),
    EmailAccount(email="carol@team.com", ...)
]

def log_conversation(message, thread):
    # Log all team conversations to database
    save_to_database(thread)
    notify_dashboard(message)

monitor = EmailThreadsMonitor(team_accounts, log_conversation)
monitor.start_async()
```

## Requirements

- Python 3.13+
- `imap-tools>=1.11.0`

## Architecture

The library is built with a modular architecture:

```
email_threads/
├── account.py       # Account configuration
├── message.py       # Message data structure
├── storage.py       # Thread-safe storage
├── reply_chain.py   # Thread construction
├── sender.py        # SMTP sending
└── monitor.py       # IMAP monitoring
```

**Key Design Decisions:**

1. **Multi-threading**: Each account has its own monitoring thread
2. **IMAP IDLE**: Real-time notifications with minimal server load
3. **In-memory storage**: Fast access, bounded memory usage
4. **Account equality**: No hardcoded roles or hierarchies
5. **Clean separation**: Monitoring and sending are independent

## Limitations

- **No persistence**: Messages are lost when the program stops
- **Memory-only**: Not suitable for very large email volumes
- **No historical data**: Only monitors emails received after startup
- **Reply chain gaps**: If parent emails aren't in storage, threads will be incomplete

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - see LICENSE file for details.

## Support

For questions or issues, please:
- Open an issue on GitHub
- Check the documentation
- Review the examples in the repository

---

**Note**: Always use app-specific passwords or authorization codes for email accounts, not your main account password. Enable IMAP/SMTP access in your email provider settings before using this library.

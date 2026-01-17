import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.core.config_manager import get_config
from src.integrations.email.imap_client import IMAPClient
from src.monitoring.logger import ScapinLogger, LogLevel


def test_fetch():
    # Configure logging
    ScapinLogger.configure(level=LogLevel.DEBUG)

    config = get_config()
    enabled_accounts = config.email.get_enabled_accounts()

    if not enabled_accounts:
        print("No enabled accounts found")
        return

    account = enabled_accounts[0]
    print(f"Testing account: {account.account_name} ({account.imap_username})")

    client = IMAPClient(account)
    try:
        with client.connect():
            print("Connected successfully via context manager")

            # The client should have a _connection attribute now
            if hasattr(client, "_connection"):
                print("Selecting INBOX...")
                client._connection.select("INBOX", readonly=True)

                status, messages = client._connection.uid("SEARCH", None, "ALL")
                print(f"Direct UID Search status: {status}")
                if status == "OK":
                    idsArr = messages[0].split()
                    print(f"Total messages in inbox: {len(idsArr)}")
                    if len(idsArr) > 0:
                        print(f"Last 5 message UIDs: {idsArr[-5:]}")

            # Test fetch_emails
            print("\nTesting fetch_emails(limit=5)...")

            print("--- Fetching UNSEEN ---")
            emails_unseen = client.fetch_emails(limit=5, unread_only=True)
            print(f"Fetched {len(emails_unseen)} unseen emails")
            for i, (meta, content) in enumerate(emails_unseen):
                print(f"  {i + 1}. [{meta.message_id}] {meta.subject}")

            print("\n--- Fetching UNPROCESSED (default) ---")
            emails = client.fetch_emails(limit=5, unprocessed_only=True)
            print(f"Fetched {len(emails)} unprocessed emails")

            for i, (meta, content) in enumerate(emails):
                print(f"  {i + 1}. [{meta.message_id}] {meta.subject}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_fetch()

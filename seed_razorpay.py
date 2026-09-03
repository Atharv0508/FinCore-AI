import json
import getpass
import time
from pathlib import Path

import razorpay


DATA_FILE = Path(__file__).parent / "mock_finance_dataset.json"

# Start conservatively. Increase later if needed.
DELAY_BETWEEN_REQUESTS = 2.0
MAX_RETRIES = 6


def create_invoice_with_retry(client, payload):
    """Create an invoice with retry handling for rate limits."""

    for attempt in range(MAX_RETRIES):
        try:
            return client.invoice.create(data=payload)

        except Exception as e:
            error_text = str(e).lower()

            if "too many requests" in error_text or "429" in error_text:
                wait_time = min(5 * (2 ** attempt), 60)

                print(
                    f"    Rate limited (429). "
                    f"Waiting {wait_time}s before retry..."
                )

                time.sleep(wait_time)
                continue

            raise

    raise Exception("Maximum retry attempts exceeded.")


def get_existing_invoices(client):
    """Fetch existing invoices so we don't create duplicates."""

    existing = {}

    try:
        skip = 0
        count = 100

        while True:
            response = client.invoice.all({
                "count": count,
                "skip": skip
            })

            items = response.get("items", [])

            for invoice in items:
                receipt = invoice.get("receipt")

                if receipt:
                    existing[receipt] = invoice

            if len(items) < count:
                break

            skip += count

        return existing

    except Exception as e:
        print(f"WARNING: Could not fetch existing invoices: {e}")
        return existing


def main():

    print("=" * 65)
    print("        RAZORPAY TEST MODE SEEDER")
    print("=" * 65)

    # ---------------------------------------------------------
    # Credentials
    # ---------------------------------------------------------

    key_id = input(
        "\nEnter Razorpay TEST Key ID: "
    ).strip()

    key_secret = getpass.getpass(
        "Enter Razorpay TEST Key Secret: "
    ).strip()

    if not key_id.startswith("rzp_test_"):
        print("\nWARNING:")
        print("The key does not look like a Razorpay TEST key.")

        confirm = input(
            "Continue anyway? (y/n): "
        ).strip().lower()

        if confirm != "y":
            print("Cancelled.")
            return

    client = razorpay.Client(
        auth=(key_id, key_secret)
    )

    # ---------------------------------------------------------
    # Load dataset
    # ---------------------------------------------------------

    if not DATA_FILE.exists():

        print("\nERROR:")
        print("mock_finance_dataset.json was not found.")

        print("\nExpected location:")
        print(DATA_FILE)

        return

    with open(
        DATA_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    invoices = data.get("invoices", [])

    print(
        f"\nMock dataset contains {len(invoices)} invoices."
    )

    # ---------------------------------------------------------
    # Get existing Razorpay invoices
    # ---------------------------------------------------------

    print("\nChecking existing Razorpay invoices...")

    existing = get_existing_invoices(client)

    print(
        f"Found {len(existing)} existing invoices."
    )

    # ---------------------------------------------------------
    # Seed invoices
    # ---------------------------------------------------------

    created = 0
    skipped = 0
    failed = 0

    print("\nStarting invoice creation...")
    print("-" * 65)

    for index, invoice in enumerate(
        invoices,
        start=1
    ):

        receipt = invoice["invoice_id"]

        # -----------------------------------------------------
        # Duplicate protection
        # -----------------------------------------------------

        if receipt in existing:

            print(
                f"[{index:02d}/{len(invoices)}] "
                f"SKIP {receipt} "
                f"(already exists as {existing[receipt]['id']})"
            )

            skipped += 1
            continue

        amount = int(invoice["amount"]) * 100

        payload = {
            "type": "invoice",

            "description":
                f"Mock Finance Controller Invoice {receipt}",

            "customer": {
                "name": invoice["customer_name"],
                "email": invoice["customer_email"]
            },

            "line_items": [
                {
                    "name": f"Test Service {index}",
                    "description":
                        "AI Finance Controller test transaction",
                    "amount": amount,
                    "currency": "INR",
                    "quantity": 1
                }
            ],

            "receipt": receipt,

            "sms_notify": False,
            "email_notify": False
        }

        try:

            result = create_invoice_with_retry(
                client,
                payload
            )

            print(
                f"[{index:02d}/{len(invoices)}] "
                f"CREATED {result['id']} "
                f"| ₹{invoice['amount']}"
            )

            created += 1

            # Important: don't hammer Razorpay
            time.sleep(DELAY_BETWEEN_REQUESTS)

        except Exception as e:

            print(
                f"[{index:02d}/{len(invoices)}] "
                f"FAILED {receipt}: {e}"
            )

            failed += 1

            # Give the API some breathing room
            time.sleep(5)

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------

    print("\n")
    print("=" * 65)
    print("                 SEEDING COMPLETE")
    print("=" * 65)

    print(f"Created : {created}")
    print(f"Skipped : {skipped}")
    print(f"Failed  : {failed}")
    print(f"Total   : {len(invoices)}")

    print("=" * 65)

    if failed == 0:

        print(
            "\nSUCCESS: All invoices are now available "
            "in your Razorpay Test account."
        )

    else:

        print(
            "\nSome invoices failed."
        )

        print(
            "Wait a few minutes and run the script again."
        )

        print(
            "Already-created invoices will be skipped."
        )


if __name__ == "__main__":
    main()
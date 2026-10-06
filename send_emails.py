"""
send_emails.py

Reads the already-generated personalized_emails.csv (columns: Company,
Email, Website, ResearchSummary, Subject, Body, ResearchStatus) and sends
each row's Subject/Body as an email with the CV attached.

This script never generates or modifies personalized_emails.csv - it only
reads it. Configure the CONFIG section below before running.

Set DRY_RUN = True to validate and preview the rows without connecting to
SMTP or sending anything. Set DRY_RUN = False to actually send the emails
over SMTP.
"""

import csv
import os
import smtplib
import sys
import time
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

# Make stdout tolerant of Unicode characters even on Windows consoles using
# a legacy codepage that can't encode them.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

# Load SENDER_EMAIL / SENDER_PASSWORD (and any other overrides) from a local
# .env file, if present, without overriding variables already set in the
# environment.
load_dotenv()

# =========================================================================
# CONFIG - edit these values before running
# =========================================================================

# --- SMTP settings ---
SMTP_SERVER = "smtp.ethereal.email"     # Ethereal test SMTP server
SMTP_PORT = 587                         # e.g. 587 for STARTTLS, 465 for SSL

# --- Sender credentials ---
# Do NOT hardcode credentials here. Set them via a local .env file or as
# environment variables instead:
#   Windows (PowerShell):  $env:SENDER_EMAIL = "you@example.com"
#                           $env:SENDER_PASSWORD = "your-app-password"
#   macOS/Linux:            export SENDER_EMAIL="you@example.com"
#                           export SENDER_PASSWORD="your-app-password"
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")

# --- CV attachment ---
CV_PATH = "CV_AHMED_BEN_BETTAIEB.pdf"

# --- Input CSV (already generated - this script only reads it) ---
PERSONALIZED_CSV_PATH = "personalized_emails.csv"

# --- Sending behavior ---
DELAY_BETWEEN_EMAILS_SECONDS = 5

# --- Dry run mode ---
# True  -> read and validate personalized_emails.csv, preview rows, send nothing.
# False -> read personalized_emails.csv and actually send the emails over SMTP.
DRY_RUN = False

# =========================================================================
# SCRIPT LOGIC - no need to edit below this line
# =========================================================================


def validate_credentials():
    """Ensure SENDER_EMAIL and SENDER_PASSWORD env vars are set. Exit with a clear error otherwise."""
    missing = [
        name for name, value in (
            ("SENDER_EMAIL", SENDER_EMAIL),
            ("SENDER_PASSWORD", SENDER_PASSWORD),
        )
        if not value
    ]
    if missing:
        print(
            "[ERROR] Missing required environment variable(s): "
            + ", ".join(missing)
            + "\nSet them before running, e.g.:\n"
            + "  Windows (PowerShell):  $env:SENDER_EMAIL = \"you@example.com\"\n"
            + "                         $env:SENDER_PASSWORD = \"your-app-password\"\n"
            + "  macOS/Linux:           export SENDER_EMAIL=\"you@example.com\"\n"
            + "                         export SENDER_PASSWORD=\"your-app-password\""
        )
        sys.exit(1)


def read_personalized_recipients(csv_path):
    """Read all rows from personalized_emails.csv. Does not modify the file."""
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def build_message(subject, body, recipient_email):
    """Build the EmailMessage with subject, body, and CV attached."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient_email
    msg.set_content(body)

    cv_file = Path(CV_PATH)
    if cv_file.exists():
        with open(cv_file, "rb") as f:
            cv_data = f.read()
        msg.add_attachment(
            cv_data,
            maintype="application",
            subtype="pdf",
            filename=cv_file.name,
        )
    else:
        print(f"[WARN] CV file not found at '{CV_PATH}' - sending without attachment.")

    return msg


def send_personalized_emails():
    """Read personalized_emails.csv and either preview it (DRY_RUN) or send it over SMTP."""
    if not Path(PERSONALIZED_CSV_PATH).exists():
        print(f"[ERROR] '{PERSONALIZED_CSV_PATH}' not found.")
        sys.exit(1)

    rows = read_personalized_recipients(PERSONALIZED_CSV_PATH)
    if not rows:
        print(f"No rows found in '{PERSONALIZED_CSV_PATH}'. Nothing to do.")
        return

    print(f"Loaded {len(rows)} personalized emails from '{PERSONALIZED_CSV_PATH}'.")
    print("-" * 60)

    total = len(rows)

    if DRY_RUN:
        valid = 0
        invalid = 0
        for i, row in enumerate(rows, start=1):
            company = (row.get("Company") or "").strip()
            email = (row.get("Email") or "").strip()
            subject = (row.get("Subject") or "").strip()
            body = (row.get("Body") or "").strip()

            if email and subject and body:
                valid += 1
            else:
                invalid += 1

            label = company or "(unknown company)"
            print(f"[{i}/{total}] {label} -> {email or '(missing email)'}")
            print(f"    Subject: {subject or '(missing subject)'}")
            preview = body.replace("\n", " ").strip()
            print(f"    Preview: {preview[:80]}{'...' if len(preview) > 80 else ''}")

        print("-" * 60)
        print("Validation complete.")
        print(f"Valid emails: {valid}")
        print(f"Invalid emails: {invalid}")
        return

    validate_credentials()

    smtp_conn = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    smtp_conn.starttls()
    smtp_conn.login(SENDER_EMAIL, SENDER_PASSWORD)

    try:
        for i, row in enumerate(rows, start=1):
            email = (row.get("Email") or "").strip()
            subject = (row.get("Subject") or "").strip()
            body = (row.get("Body") or "").strip()

            if not email or not subject or not body:
                print(f"[{i}/{total}] SKIPPED - missing Email/Subject/Body in CSV row")
                continue

            msg = build_message(subject, body, email)

            try:
                smtp_conn.send_message(msg)
                print(f"[{i}/{total}] SUCCESS - sent to {email}")
            except Exception as e:
                print(f"[{i}/{total}] FAILED - {email} - {e}")

            if i < total:
                time.sleep(DELAY_BETWEEN_EMAILS_SECONDS)
    finally:
        smtp_conn.quit()

    print("-" * 60)
    print("Done.")


def main():
    print(f"DRY_RUN = {DRY_RUN}")
    send_personalized_emails()


if __name__ == "__main__":
    main()

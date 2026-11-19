"""Interactive seed script to create the initial administrator account.
No default passwords are hardcoded or shipped.
The script asks for credentials interactively (with CLI argument support for automation).
"""

import sys
import os
import getpass
import argparse

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
import models
import auth


def seed_admin():
    parser = argparse.ArgumentParser(description="Create the initial administrator account for ASSETRA.")
    parser.add_argument("--name", type=str, default=None, help="Admin full name")
    parser.add_argument("--email", type=str, default=None, help="Admin email address")
    parser.add_argument("--password", type=str, default=None, help="Admin password (leave blank to be prompted securely)")

    args = parser.parse_args()

    print("==================================================")
    print("      ASSETRA - Initial Administrator Setup       ")
    print("==================================================")

    # 1. Prompt for Name
    name = args.name
    if not name:
        while True:
            if sys.stdin.isatty():
                name = input("Enter Admin Full Name: ").strip()
            else:
                name = os.getenv("ADMIN_NAME", "").strip()
            if name:
                break
            print("Error: Name is required.")
            if not sys.stdin.isatty():
                sys.exit(1)

    # 2. Prompt for Email
    email = args.email
    if not email:
        while True:
            if sys.stdin.isatty():
                email = input("Enter Admin Email address: ").strip().lower()
            else:
                email = os.getenv("ADMIN_EMAIL", "").strip().lower()

            if not email:
                print("Error: Email is required.")
                if not sys.stdin.isatty():
                    sys.exit(1)
                continue

            if not auth.is_domain_allowed(email):
                allowed = ", ".join(auth.get_allowed_email_domains())
                print(f"Error: Email domain is not allowed. Permitted domains: {allowed}")
                if not sys.stdin.isatty():
                    sys.exit(1)
                continue
            break
    else:
        email = email.strip().lower()
        if not auth.is_domain_allowed(email):
            allowed = ", ".join(auth.get_allowed_email_domains())
            print(f"Error: Email domain is not allowed. Permitted domains: {allowed}")
            sys.exit(1)

    # 3. Prompt for Password
    password = args.password
    if not password:
        password = os.getenv("ADMIN_PASSWORD")

    if not password:
        min_p_len = auth.get_password_min_length()
        while True:
            if not sys.stdin.isatty():
                print("Error: No password provided in non-interactive mode. Use --password or ADMIN_PASSWORD env var.")
                sys.exit(1)

            pwd1 = getpass.getpass(f"Enter Admin Password (min {min_p_len} characters): ")
            pwd2 = getpass.getpass("Confirm Admin Password: ")

            if pwd1 != pwd2:
                print("Error: Passwords do not match. Please try again.\n")
                continue

            is_valid, err_msg = auth.validate_password_strength(pwd1, email=email)
            if not is_valid:
                print(f"Error: {err_msg} Please try again.\n")
                continue

            password = pwd1
            break
    else:
        is_valid, err_msg = auth.validate_password_strength(password, email=email)
        if not is_valid:
            print(f"Error: {err_msg}")
            sys.exit(1)

    # 4. Save to Database
    db = SessionLocal()
    try:
        existing = db.query(models.User).filter(models.User.email == email).first()
        if existing:
            print(f"\nUser with email '{email}' already exists (ID: {existing.id}, Role: {existing.role}, Status: {existing.status}).")
            if sys.stdin.isatty():
                confirm = input("Do you want to update this user's password and elevate to admin? [y/N]: ").strip().lower()
            else:
                confirm = "y"

            if confirm in ("y", "yes"):
                existing.name = name
                existing.role = "admin"
                existing.status = "active"
                existing.is_active = True
                existing.password_hash = auth.hash_password(password)
                existing.must_change_password = False
                
                auth.record_audit_event(
                    db=db,
                    actor_id=existing.id,
                    action="admin_updated_via_seed",
                    target=f"user:{existing.id}:{existing.email}"
                )
                db.commit()
                print(f"Admin account '{email}' updated and activated successfully!")
            else:
                print("Operation cancelled. No changes made.")
            return

        admin_user = models.User(
            name=name,
            email=email,
            password_hash=auth.hash_password(password),
            role="admin",
            status="active",
            is_active=True,
            must_change_password=False
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        auth.record_audit_event(
            db=db,
            actor_id=admin_user.id,
            action="initial_admin_seeded",
            target=f"user:{admin_user.id}:{admin_user.email}"
        )

        print("\nSuccess: Administrator created successfully!")
        print(f"  ID:     {admin_user.id}")
        print(f"  Name:   {admin_user.name}")
        print(f"  Email:  {admin_user.email}")
        print(f"  Role:   {admin_user.role}")
        print(f"  Status: {admin_user.status}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()

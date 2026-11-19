"""Comprehensive test suite for Authentication, Sign-up, Approval workflow,
Rate limiting, and Security protections.
"""

import os
import sys

# Test database isolation guard
import test_guard

import uuid
import secrets
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from main import app
from database import SessionLocal
import models
import auth

client = TestClient(app)

def test_full_auth_and_signup_flow():
    print("\n========================================================")
    print("      RUNNING FAR AUTH & SIGNUP TEST SUITE              ")
    print("========================================================")

    db = SessionLocal()
    try:
        # 0. Ensure an active Admin exists
        admin_user = db.query(models.User).filter(models.User.role == "admin", models.User.status == "active").first()
        if not admin_user:
            admin_user = models.User(
                name="Test Admin Fixture",
                email="test_fixture_admin@far.test",
                email_canonical="test_fixture_admin@far.test",
                password_hash=auth.hash_password(secrets.token_urlsafe(16)),
                role="admin",
                status="active",
                is_active=True,
                email_verified=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

        admin_token = auth.create_access_token(data={"sub": str(admin_user.id), "role": "admin"})
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print(f"  [PASS] 0. Administrator session authenticated for Admin #{admin_user.id}.")

        # ----------------------------------------------------
        # TEST 1: Sign up a new user with pending status & user role
        # ----------------------------------------------------
        test_uid = uuid.uuid4().hex[:6]
        user_email = f"user_{test_uid}@shareindia.com"
        user_pwd = f"UserPassSafe@{test_uid}2026"

        signup_res = client.post(
            "/auth/signup",
            headers={"X-Forwarded-For": "10.0.1.50"},
            json={
                "name": f"Test User {test_uid}",
                "email": user_email,
                "password": user_pwd,
                "confirm_password": user_pwd
            }
        )
        assert signup_res.status_code == 200, f"Sign-up failed: {signup_res.text}"
        signup_data = signup_res.json()
        assert "submitted for admin approval" in signup_data["message"]

        # Verify DB record
        created_user = db.query(models.User).filter(models.User.email == user_email).first()
        assert created_user is not None
        assert created_user.role == "user"
        assert created_user.status == "pending"
        assert created_user.is_active is False
        print(f"  [PASS] 1. Sign up creates user '{user_email}' with role='user', status='pending'.")

        # ----------------------------------------------------
        # TEST 2: Confirm login is BLOCKED with approval message
        # ----------------------------------------------------
        login_blocked_res = client.post(
            "/auth/login",
            json={"email": user_email, "password": user_pwd}
        )
        assert login_blocked_res.status_code == 403, f"Expected 403, got {login_blocked_res.status_code}"
        assert "Your account is awaiting admin approval." in login_blocked_res.json()["detail"]
        print(f"  [PASS] 2. Login is blocked for pending user with: '{login_blocked_res.json()['detail']}'.")

        # ----------------------------------------------------
        # TEST 3: Admin Approves the user
        # ----------------------------------------------------
        approve_res = client.post(
            f"/admin/users/{created_user.id}/approve",
            headers=admin_headers
        )
        assert approve_res.status_code == 200, f"Approval failed: {approve_res.text}"
        approve_data = approve_res.json()
        assert approve_data["user"]["status"] == "active"

        # Rollback test session to clear REPEATABLE READ snapshot from MySQL
        db.rollback()
        updated_user = db.query(models.User).filter(models.User.id == created_user.id).first()
        assert updated_user.status == "active"
        assert updated_user.is_active is True

        # Check audit log
        audit = db.query(models.AuditLog).filter(
            models.AuditLog.action == "user_approved",
            models.AuditLog.target.like(f"%{user_email}%")
        ).first()
        assert audit is not None, "Audit log missing for approval action"
        print(f"  [PASS] 3. Admin approved user '{user_email}'. Status is now 'active', audit logged.")

        # ----------------------------------------------------
        # TEST 4: Confirm login WORKS after approval
        # ----------------------------------------------------
        login_success_res = client.post(
            "/auth/login",
            json={"email": user_email, "password": user_pwd}
        )
        assert login_success_res.status_code == 200, f"Expected 200, got {login_success_res.status_code}"
        login_data = login_success_res.json()
        assert "token" in login_data
        assert login_data["user"]["email"] == user_email
        assert login_data["user"]["status"] == "active"
        print("  [PASS] 4. Approved user can log in successfully and receive JWT token.")

        # ----------------------------------------------------
        # TEST 5: Duplicate email returns identical response (no leak)
        # ----------------------------------------------------
        dup_pwd = f"DupPass_{secrets.token_hex(4)}!Aa1"
        dup_res = client.post(
            "/auth/signup",
            headers={"X-Forwarded-For": "10.0.1.51"},
            json={
                "name": "Different Name",
                "email": user_email,
                "password": dup_pwd,
                "confirm_password": dup_pwd
            }
        )
        assert dup_res.status_code == 200
        assert dup_res.json()["message"] == signup_data["message"]
        # Ensure the original user details were untouched
        db.rollback()
        check_user = db.query(models.User).filter(models.User.id == created_user.id).first()
        assert check_user.name == f"Test User {test_uid}"
        print("  [PASS] 5. Duplicate email returns identical response; user enumeration prevented.")

        # ----------------------------------------------------
        # TEST 6: Disallowed email domain is rejected
        # ----------------------------------------------------
        sec_pwd = f"SecPass_{secrets.token_hex(4)}!Aa1"
        disallowed_res = client.post(
            "/auth/signup",
            headers={"X-Forwarded-For": "10.0.1.52"},
            json={
                "name": "External Hacker",
                "email": "hacker@disalloweddomain1234.net",
                "password": sec_pwd,
                "confirm_password": sec_pwd
            }
        )
        assert disallowed_res.status_code == 400
        assert "restricted to authorized company domains" in disallowed_res.json()["detail"]
        print(f"  [PASS] 6. Disallowed domain correctly rejected with 400: '{disallowed_res.json()['detail']}'.")

        # ----------------------------------------------------
        # TEST 7: Sending role=admin in sign-up request has NO effect
        # ----------------------------------------------------
        tamper_uid = uuid.uuid4().hex[:6]
        tamper_email = f"tamper_{tamper_uid}@shareindia.com"
        tamper_pwd = f"TampPass_{secrets.token_hex(4)}!Aa1"
        tamper_res = client.post(
            "/auth/signup",
            headers={"X-Forwarded-For": "10.0.1.53"},
            json={
                "name": "Privilege Escalator",
                "email": tamper_email,
                "password": tamper_pwd,
                "confirm_password": tamper_pwd,
                "role": "admin",
                "status": "active"
            }
        )
        assert tamper_res.status_code == 200
        db.rollback()
        tamper_user = db.query(models.User).filter(models.User.email == tamper_email).first()
        assert tamper_user is not None
        assert tamper_user.role == "user", f"Privilege escalation occurred! Role is {tamper_user.role}"
        assert tamper_user.status == "pending", f"Status tampering occurred! Status is {tamper_user.status}"
        print("  [PASS] 7. Privilege escalation denied: role='admin' ignored; user created as role='user', status='pending'.")

        # ----------------------------------------------------
        # TEST 8: Rate limiting (5 per hour per IP)
        # ----------------------------------------------------
        rate_test_ip = "192.0.2.77"
        rate_responses = []
        for i in range(6):
            rate_pwd = f"RatePass_{secrets.token_hex(4)}!Aa1"
            r = client.post(
                "/auth/signup",
                headers={"X-Forwarded-For": rate_test_ip},
                json={
                    "name": f"Rate Limit Test {i}",
                    "email": f"ratetest_{i}_{uuid.uuid4().hex[:4]}@shareindia.com",
                    "password": rate_pwd,
                    "confirm_password": rate_pwd
                }
            )
            rate_responses.append(r.status_code)

        assert rate_responses[:5] == [200, 200, 200, 200, 200], f"First 5 should succeed, got {rate_responses[:5]}"
        assert rate_responses[5] == 429, f"6th sign-up should be 429 Too Many Requests, got {rate_responses[5]}"
        print("  [PASS] 8. Rate limiting enforced: Attempts 1-5 succeed (200), attempt 6 blocked with 429.")

        # ----------------------------------------------------
        # TEST 9: Project-wide search for forbidden credentials
        # ----------------------------------------------------
        import subprocess
        res = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "search_forbidden_terms.py")],
            capture_output=True,
            text=True
        )
        assert res.returncode == 0, f"Credential check failed: {res.stdout}\n{res.stderr}"
        print("  [PASS] 9. Project-wide scan for default credentials returns 0 matches.")

        print("\n========================================================")
        print("      ALL 9 VERIFICATION TESTS PASSED SUCCESSFULLY!     ")
        print("========================================================\n")
    finally:
        db.close()


if __name__ == "__main__":
    test_full_auth_and_signup_flow()

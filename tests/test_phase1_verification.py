import os
import sys

# Test database isolation guard
import test_guard

import unittest
import secrets
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import models
import auth
from database import SessionLocal
import email_service
from main import app

TEST_PASSWORD = f"Tst_{secrets.token_hex(4)}!Aa1"
ALT_PASSWORD = f"Alt_{secrets.token_hex(4)}!Bb2"
NEW_PASSWORD = f"New_{secrets.token_hex(4)}!Cc3"

class TestPhase1Verification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        email_service.set_test_mode(True)
        cls.client = TestClient(app)
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        email_service.set_test_mode(False)
        cls.db.close()

    def setUp(self):
        auth._signup_attempts.clear()

    def test_01_signup_and_receive_code(self):
        """Test sign-up creates pending_verification user, hashed code, and dispatches email."""
        test_email = "test_signup_user@example.com"
        self.db.query(models.User).filter(models.User.email == test_email).delete()
        self.db.commit()

        signup_payload = {
            "name": "Signup User",
            "email": test_email,
            "password": TEST_PASSWORD,
            "confirm_password": TEST_PASSWORD,
            "consented": True
        }
        res = self.client.post("/auth/signup", json=signup_payload)
        self.assertEqual(res.status_code, 200, f"Signup failed: {res.text}")
        self.assertIn("6-digit verification code has been sent", res.json()["message"])

        # Check user in DB
        user = self.db.query(models.User).filter(models.User.email == test_email).first()
        self.assertIsNotNone(user, "User was not created in DB")
        self.assertEqual(user.status, "pending_verification")
        self.assertFalse(user.email_verified)
        self.assertEqual(user.role, "user")
        self.assertEqual(user.auth_provider, "password")
        self.assertIsNotNone(user.consented_at)
        self.assertEqual(user.terms_version, "1.0")

        # Check code in email_verification_codes table
        code_entry = self.db.query(models.EmailVerificationCode).filter(
            models.EmailVerificationCode.user_id == user.id
        ).order_by(models.EmailVerificationCode.id.desc()).first()
        self.assertIsNotNone(code_entry)
        self.assertEqual(len(code_entry.code_hash), 64, "Code hash must be 64-char SHA256")
        self.assertEqual(code_entry.attempts, 0)
        self.assertIsNone(code_entry.used_at)

        # Check email service recorded the code
        email_info = email_service.get_last_test_email(test_email)
        self.assertIsNotNone(email_info, "Email was not recorded by email service")
        self.assertIn("code", email_info)
        code = email_info["code"]
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_02_verify_code_and_login(self):
        """Test verifying the 6-digit code activates the account and allows login."""
        test_email = "test_verify_user@example.com"
        self.db.query(models.User).filter(models.User.email == test_email).delete()
        self.db.commit()

        # 1. Sign up
        self.client.post("/auth/signup", json={
            "name": "Verify User",
            "email": test_email,
            "password": TEST_PASSWORD,
            "confirm_password": TEST_PASSWORD,
            "consented": True
        })

        # 2. Before verification, login must be blocked (403 pending_verification)
        login_res_blocked = self.client.post("/auth/login", json={
            "email": test_email,
            "password": TEST_PASSWORD
        })
        self.assertEqual(login_res_blocked.status_code, 403)
        self.assertIn("Please verify your email address", login_res_blocked.json()["detail"])

        # 3. Retrieve code from email service
        email_info = email_service.get_last_test_email(test_email)
        self.assertIsNotNone(email_info)
        code = email_info["code"]

        # 4. Submit verification code
        verify_res = self.client.post("/auth/verify-code", json={
            "email": test_email,
            "code": code
        })
        self.assertEqual(verify_res.status_code, 200, f"Verification failed: {verify_res.text}")
        verify_data = verify_res.json()
        self.assertEqual(verify_data["user"]["status"], "active")
        self.assertTrue(verify_data["user"]["email_verified"])
        self.assertIn("token", verify_data)

        # 5. Check DB state
        self.db.expire_all()
        user = self.db.query(models.User).filter(models.User.email == test_email).first()
        self.assertEqual(user.status, "active")
        self.assertTrue(user.email_verified)
        self.assertTrue(user.is_active)

        # Code entry should now be marked as used
        code_entry = self.db.query(models.EmailVerificationCode).filter(
            models.EmailVerificationCode.user_id == user.id
        ).order_by(models.EmailVerificationCode.id.desc()).first()
        self.assertIsNotNone(code_entry.used_at)

        # 6. Login should now succeed
        login_res = self.client.post("/auth/login", json={
            "email": test_email,
            "password": TEST_PASSWORD
        })
        self.assertEqual(login_res.status_code, 200)
        self.assertEqual(login_res.json()["user"]["email"], test_email)

    def test_03_wrong_codes_lock_after_5_attempts(self):
        """Test entering wrong verification codes locks out after 5 failed attempts."""
        test_email = "test_lockout_user@example.com"
        self.db.query(models.User).filter(models.User.email == test_email).delete()
        self.db.commit()

        # Sign up
        self.client.post("/auth/signup", json={
            "name": "Lockout User",
            "email": test_email,
            "password": ALT_PASSWORD,
            "confirm_password": ALT_PASSWORD,
            "consented": True
        })

        # Submit wrong code 4 times (expect remaining attempts warning)
        for _ in range(4):
            res = self.client.post("/auth/verify-code", json={
                "email": test_email,
                "code": "000000"
            })
            self.assertEqual(res.status_code, 400)
            self.assertIn("Invalid verification code", res.json()["detail"])

        # 5th failed attempt
        res5 = self.client.post("/auth/verify-code", json={
            "email": test_email,
            "code": "000000"
        })
        self.assertEqual(res5.status_code, 400)

        # 6th attempt should now be explicitly locked
        res6 = self.client.post("/auth/verify-code", json={
            "email": test_email,
            "code": "000000"
        })
        self.assertEqual(res6.status_code, 400)
        self.assertIn("locked", res6.json()["detail"].lower())

    def test_04_anti_enumeration(self):
        """Test identical responses for existing vs non-existing emails on signup, forgot-password, and resend."""
        test_email = "test_antienum_user@example.com"
        unknown_email = "nonexistent_ghost_user_12345@example.com"

        self.db.query(models.User).filter(models.User.email == test_email).delete()
        self.db.commit()

        # Create user
        signup_res1 = self.client.post("/auth/signup", headers={"X-Forwarded-For": "192.168.10.1"}, json={
            "name": "Existing User",
            "email": test_email,
            "password": TEST_PASSWORD,
            "confirm_password": TEST_PASSWORD,
            "consented": True
        })
        self.assertEqual(signup_res1.status_code, 200)

        # Offset previous code created_at by 65s to respect 60s cooldown
        user1 = self.db.query(models.User).filter(models.User.email == test_email).first()
        self.db.query(models.EmailVerificationCode).filter(models.EmailVerificationCode.user_id == user1.id).update({
            "created_at": datetime.now(timezone.utc) - timedelta(seconds=65)
        })
        self.db.commit()

        # 1. Signup identical response when already exists
        signup_res2 = self.client.post("/auth/signup", headers={"X-Forwarded-For": "192.168.10.2"}, json={
            "name": "Duplicate User",
            "email": test_email,
            "password": ALT_PASSWORD,
            "confirm_password": ALT_PASSWORD,
            "consented": True
        })
        self.assertEqual(signup_res2.status_code, 200)
        self.assertIn("verification code has been sent", signup_res2.json()["message"])

        # 2. Forgot-password identical response
        forgot_res_existing = self.client.post("/auth/forgot-password", json={"email": test_email})
        forgot_res_unknown = self.client.post("/auth/forgot-password", json={"email": unknown_email})
        self.assertEqual(forgot_res_existing.status_code, 200)
        self.assertEqual(forgot_res_unknown.status_code, 200)
        self.assertEqual(forgot_res_existing.json()["message"], forgot_res_unknown.json()["message"])

        # 3. Resend-code identical response (offset previous code created_at by 65s to respect 60s cooldown)
        user = self.db.query(models.User).filter(models.User.email == test_email).first()
        self.db.query(models.EmailVerificationCode).filter(models.EmailVerificationCode.user_id == user.id).update({
            "created_at": datetime.now(timezone.utc) - timedelta(seconds=65)
        })
        self.db.commit()

        resend_existing = self.client.post("/auth/resend-code", json={"email": test_email})
        resend_unknown = self.client.post("/auth/resend-code", json={"email": unknown_email})
        self.assertEqual(resend_existing.status_code, 200)
        self.assertEqual(resend_unknown.status_code, 200)
        self.assertEqual(resend_existing.json()["message"], resend_unknown.json()["message"])

    def test_05_password_reset_end_to_end_and_session_invalidation(self):
        """Test password reset token issuance, reset completion, and session invalidation."""
        test_email = "test_pw_reset_user@example.com"
        old_password = TEST_PASSWORD
        new_password = NEW_PASSWORD

        self.db.query(models.User).filter(models.User.email == test_email).delete()
        self.db.commit()

        # 1. Sign up & verify
        self.client.post("/auth/signup", json={
            "name": "Reset User",
            "email": test_email,
            "password": old_password,
            "confirm_password": old_password,
            "consented": True
        })
        email_info = email_service.get_last_test_email(test_email)
        self.assertIsNotNone(email_info)
        code = email_info["code"]
        self.client.post("/auth/verify-code", json={"email": test_email, "code": code})

        # 2. Log in to get active session JWT
        login_res = self.client.post("/auth/login", json={
            "email": test_email,
            "password": old_password
        })
        self.assertEqual(login_res.status_code, 200)
        old_jwt_token = login_res.json()["token"]

        # 3. Verify old token works before reset
        me_res = self.client.get("/auth/me", headers={"Authorization": f"Bearer {old_jwt_token}"})
        self.assertEqual(me_res.status_code, 200)

        # 4. Request forgot-password
        forgot_res = self.client.post("/auth/forgot-password", json={"email": test_email})
        self.assertEqual(forgot_res.status_code, 200)

        # 5. Retrieve token from email service
        reset_email_info = email_service.get_last_test_email(test_email)
        self.assertIsNotNone(reset_email_info)
        reset_token = reset_email_info.get("token")
        self.assertIsNotNone(reset_token)

        # Check DB token storage: token_hash length 64, not plaintext
        token_entry = self.db.query(models.PasswordResetToken).filter(
            models.PasswordResetToken.user_id == me_res.json()["id"]
        ).order_by(models.PasswordResetToken.id.desc()).first()
        self.assertIsNotNone(token_entry)
        self.assertEqual(len(token_entry.token_hash), 64)
        self.assertNotEqual(token_entry.token_hash, reset_token)

        # 6. Reset password with valid token
        reset_res = self.client.post("/auth/reset-password", json={
            "token": reset_token,
            "new_password": new_password,
            "confirm_password": new_password,
            "email": test_email
        })
        self.assertEqual(reset_res.status_code, 200, f"Reset failed: {reset_res.text}")
        self.assertIn("reset successfully", reset_res.json()["message"].lower())

        # 7. Verify token is single-use: repeating reset must fail
        reuse_res = self.client.post("/auth/reset-password", json={
            "token": reset_token,
            "new_password": new_password,
            "confirm_password": new_password,
            "email": test_email
        })
        self.assertEqual(reuse_res.status_code, 400)

        # 8. Verify old session token is now invalid (Session invalidation on reset)
        me_after_res = self.client.get("/auth/me", headers={"Authorization": f"Bearer {old_jwt_token}"})
        self.assertEqual(me_after_res.status_code, 401, "Old session was not invalidated after password reset")

        # 9. Verify old password no longer works
        old_login = self.client.post("/auth/login", json={"email": test_email, "password": old_password})
        self.assertEqual(old_login.status_code, 401)

        # 10. Verify new password works
        new_login = self.client.post("/auth/login", json={"email": test_email, "password": new_password})
        self.assertEqual(new_login.status_code, 200)

if __name__ == "__main__":
    unittest.main()

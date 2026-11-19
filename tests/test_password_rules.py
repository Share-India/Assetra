import os
import sys

# Test database isolation guard
import test_guard

import unittest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import auth
import models
from database import SessionLocal
import email_service
from main import app

class TestPasswordRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_backend_validator_unit_checks(self):
        """Test validate_password_strength directly."""
        # 1. 5-character password rejected
        valid, msg = auth.validate_password_strength("Ab123", email="user@example.com")
        self.assertFalse(valid)
        self.assertEqual(msg, "Password must be at least 6 characters long.")

        # 2. 6-character valid password accepted
        valid, msg = auth.validate_password_strength("Ab12#x", email="user@example.com")
        self.assertTrue(valid)
        self.assertEqual(msg, "")

        # 3. 123456 rejected as too common
        valid, msg = auth.validate_password_strength("123456", email="user@example.com")
        self.assertFalse(valid)
        self.assertIn("too common", msg.lower())

        # 4. Other 6-char common passwords rejected
        for common in ["111111", "000000", "654321", "qwerty", "password"]:
            valid, msg = auth.validate_password_strength(common, email="user@example.com")
            self.assertFalse(valid, f"Expected {common} to be rejected")
            self.assertIn("too common", msg.lower())

        # 5. Password matching email or email username rejected
        valid, msg = auth.validate_password_strength("user123", email="user123@example.com")
        self.assertFalse(valid)
        self.assertIn("username", msg.lower())

        valid, msg = auth.validate_password_strength("user@example.com", email="user@example.com")
        self.assertFalse(valid)
        self.assertIn("email address", msg.lower())

        # 6. Password over 128 characters rejected
        valid, msg = auth.validate_password_strength("A" * 129, email="user@example.com")
        self.assertFalse(valid)
        self.assertIn("128", msg)

    def test_02_api_signup_rejects_5_char_password(self):
        """Test POST /auth/signup rejects 5-character password even if client check bypassed."""
        test_email = "test_5char@example.com"
        self.db.query(models.User).filter(models.User.email == test_email).delete()
        self.db.commit()

        res = self.client.post("/auth/signup", json={
            "name": "Five Char",
            "email": test_email,
            "password": "Ab123",
            "confirm_password": "Ab123",
            "consented": True
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Password must be at least 6 characters long.", res.json()["detail"])

    def test_03_api_signup_accepts_6_char_password(self):
        """Test POST /auth/signup accepts 6-character valid password."""
        test_email = "test_6char@example.com"
        self.db.query(models.User).filter(models.User.email == test_email).delete()
        self.db.commit()

        res = self.client.post("/auth/signup", json={
            "name": "Six Char",
            "email": test_email,
            "password": "Ab12#x",
            "confirm_password": "Ab12#x",
            "consented": True
        })
        self.assertEqual(res.status_code, 200, f"Expected 200, got: {res.text}")
        self.assertIn("6-digit verification code has been sent", res.json()["message"])

        # Clean up
        self.db.query(models.User).filter(models.User.email == test_email).delete()
        self.db.commit()

    def test_04_api_signup_rejects_123456_as_too_common(self):
        """Test POST /auth/signup rejects '123456' as too common."""
        test_email = "test_common123456@example.com"
        res = self.client.post("/auth/signup", json={
            "name": "Common Pass",
            "email": test_email,
            "password": "123456",
            "confirm_password": "123456",
            "consented": True
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("too common", res.json()["detail"].lower())

    def test_05_api_reset_password_rejects_weak_passwords(self):
        """Test POST /auth/reset-password rejects 5-char and common passwords."""
        # Test 5-char on reset
        res5 = self.client.post("/auth/reset-password", json={
            "email": "test_pw_reset@example.com",
            "token": "dummy_reset_token_longer_than_10",
            "new_password": "12345",
            "confirm_password": "12345"
        })
        self.assertEqual(res5.status_code, 400)
        self.assertIn("at least 6 characters", res5.json()["detail"])

        # Test common password on reset
        res_common = self.client.post("/auth/reset-password", json={
            "email": "test_pw_reset@example.com",
            "token": "dummy_reset_token_longer_than_10",
            "new_password": "password",
            "confirm_password": "password"
        })
        self.assertEqual(res_common.status_code, 400)
        self.assertIn("too common", res_common.json()["detail"].lower())

if __name__ == "__main__":
    unittest.main()

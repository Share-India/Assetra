import os
import sys
import unittest
import datetime

# 1. Enforce test database isolation to far_app_test
os.environ["TESTING"] = "true"
os.environ["DB_NAME"] = "far_app_test"

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(TESTS_DIR, "..", "backend"))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import test_guard
from database import engine, SessionLocal, Base
import models
from pdf_summary_generator import generate_pdf_summary_stream, fetch_grouped_data, format_inr
from routers.analyses import check_analysis_view_permission
from fastapi import HTTPException

class TestPdfSummaryOnTestDb(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

        # Create or fetch test users
        cls.owner = cls.db.query(models.User).filter_by(email="pdf_owner@example.com").first()
        if not cls.owner:
            cls.owner = models.User(
                name="PDF Owner",
                email="pdf_owner@example.com",
                email_canonical="pdf_owner@example.com",
                password_hash="fakehash",
                role="user",
                status="active",
                email_verified=True,
                is_active=True
            )
            cls.db.add(cls.owner)

        cls.other_user = cls.db.query(models.User).filter_by(email="pdf_other@example.com").first()
        if not cls.other_user:
            cls.other_user = models.User(
                name="PDF Other",
                email="pdf_other@example.com",
                email_canonical="pdf_other@example.com",
                password_hash="fakehash",
                role="user",
                status="active",
                email_verified=True,
                is_active=True
            )
            cls.db.add(cls.other_user)

        cls.admin_user = cls.db.query(models.User).filter_by(email="pdf_admin@example.com").first()
        if not cls.admin_user:
            cls.admin_user = models.User(
                name="PDF Admin",
                email="pdf_admin@example.com",
                email_canonical="pdf_admin@example.com",
                password_hash="fakehash",
                role="admin",
                status="active",
                email_verified=True,
                is_active=True
            )
            cls.db.add(cls.admin_user)

        cls.db.commit()
        cls.db.refresh(cls.owner)
        cls.db.refresh(cls.other_user)
        cls.db.refresh(cls.admin_user)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_pdf_grand_totals_equal_dashboard_exactly(self):
        """
        Verify that the PDF's grand totals exactly equal the dashboard metrics
        (total acquisition, total replacement, and rows total).
        """
        # Create test analysis
        analysis = models.Analysis(
            user_id=self.owner.id,
            company_name="Acme Precision Tools Ltd",
            original_filename="FAR_Acme_2025.xlsx",
            file_sha256="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            master_version="v6_test_hash",
            status="completed",
            rows_total=5,
            rows_calculated=4,
            rows_manual_review=1,
            total_acquisition=1500000.00,
            total_replacement=2450000.00
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        # Create rows: Building, Plant & Machinery, Software, and a Needs Review row
        test_rows = [
            models.AnalysisRow(
                analysis_id=analysis.id,
                row_no=1,
                asset_code="BLD-01",
                description="Factory Shed",
                location="Plant 1",
                wpi_group="Building",
                status="Success",
                acquisition_value=500000.00,
                replacement_value=1200000.00
            ),
            models.AnalysisRow(
                analysis_id=analysis.id,
                row_no=2,
                asset_code="MCH-01",
                description="CNC Milling Machine",
                location="Plant 1",
                wpi_group="Plant & Machinery",
                status="Success",
                acquisition_value=600000.00,
                replacement_value=900000.00
            ),
            models.AnalysisRow(
                analysis_id=analysis.id,
                row_no=3,
                asset_code="SFT-01",
                description="AutoCAD License",
                location="Plant 2",
                wpi_group="Software",
                status="Success",
                acquisition_value=100000.00,
                replacement_value=100000.00
            ),
            models.AnalysisRow(
                analysis_id=analysis.id,
                row_no=4,
                asset_code="VEH-01",
                description="Delivery Van",
                location="Plant 2",
                wpi_group="Vehicles",
                status="Success",
                acquisition_value=200000.00,
                replacement_value=250000.00
            ),
            models.AnalysisRow(
                analysis_id=analysis.id,
                row_no=5,
                asset_code="UNM-01",
                description="Unclassified Tooling",
                location="Plant 1",
                wpi_group="-",
                status="Manual Review Required",
                acquisition_value=100000.00,
                replacement_value=0.00
            ),
        ]
        self.db.bulk_save_objects(test_rows)
        self.db.commit()

        # Update analysis totals from rows to ensure perfect alignment
        analysis.total_acquisition = 1500000.00
        analysis.total_replacement = 2450000.00
        analysis.rows_total = 5
        self.db.commit()

        # Fetch grouped data exactly as PDF generator does
        grand_rows, loc_rows, distinct_locs, held = fetch_grouped_data(self.db, analysis.id)

        # 1. Check sum of rows matches dashboard values
        sum_cost = sum(r["cost"] for r in grand_rows)
        sum_rep = sum(r["replacement"] for r in grand_rows)
        sum_count = sum(r["count"] for r in grand_rows)

        self.assertEqual(sum_cost, float(analysis.total_acquisition))
        self.assertEqual(sum_rep, float(analysis.total_replacement))
        self.assertEqual(sum_count, analysis.rows_total)

        # 2. Check multiple locations detected: Plant 1 and Plant 2
        self.assertEqual(len(distinct_locs), 2)
        self.assertIn("Plant 1", loc_rows)
        self.assertIn("Plant 2", loc_rows)

        # 3. Generate PDF and verify it returns a valid stream
        stream = generate_pdf_summary_stream(analysis, self.db)
        pdf_bytes = stream.getvalue()
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_bytes), 1000)

        # Cleanup test analysis
        self.db.delete(analysis)
        self.db.commit()

    def test_permission_rules(self):
        """
        Verify permission rules:
        - Owner can download
        - Admin can download ONLY if ADMIN_CAN_VIEW_ROWS is true
        - Non-owner regular user gets 404
        """
        analysis = models.Analysis(
            user_id=self.owner.id,
            company_name="Perm Test Co",
            original_filename="test.xlsx",
            file_sha256="abc",
            master_version="v6",
            status="completed"
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        # 1. Owner should succeed without exception
        try:
            check_analysis_view_permission(analysis, self.owner)
        except Exception as e:
            self.fail(f"Owner check raised unexpected exception: {e}")

        # 2. Other user should raise 404
        with self.assertRaises(HTTPException) as ctx:
            check_analysis_view_permission(analysis, self.other_user)
        self.assertEqual(ctx.exception.status_code, 404)

        # 3. Admin when ADMIN_CAN_VIEW_ROWS is false should raise 403
        os.environ["ADMIN_CAN_VIEW_ROWS"] = "false"
        with self.assertRaises(HTTPException) as ctx:
            check_analysis_view_permission(analysis, self.admin_user)
        self.assertEqual(ctx.exception.status_code, 403)

        # 4. Admin when ADMIN_CAN_VIEW_ROWS is true should succeed
        os.environ["ADMIN_CAN_VIEW_ROWS"] = "true"
        try:
            check_analysis_view_permission(analysis, self.admin_user)
        except Exception as e:
            self.fail(f"Admin with ADMIN_CAN_VIEW_ROWS=true raised unexpected exception: {e}")
        finally:
            os.environ["ADMIN_CAN_VIEW_ROWS"] = "false"

        self.db.delete(analysis)
        self.db.commit()

if __name__ == "__main__":
    unittest.main()

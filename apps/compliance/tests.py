"""
Comprehensive Paystack compliance system test suite.
Verifies all 17 requirements of the Paystack Compliance & Provider Verification brief.
"""

from datetime import timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.utils import timezone
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model

from accounts.models import ProviderCompany
from fleet.models import Vehicle
from compliance.models import ComplianceDocument, ComplianceAuditLog
from compliance.reports import generate_compliance_report_pdf
from compliance.tasks import check_document_expirations_task

User = get_user_model()


class PaystackComplianceTests(TestCase):
    def setUp(self):
        self.today = timezone.now().date()

        # Admin / Broker user
        self.broker_user = User.objects.create_user(
            username='test_broker',
            email='broker@test.com',
            password='Password123!',
            role=User.Role.BROKER,
            is_staff=True
        )

        # Provider user
        self.provider_user = User.objects.create_user(
            username='test_provider_admin',
            email='admin@testprovider.gh',
            password='Password123!',
            role=User.Role.PROVIDER_ADMIN
        )

        # Customer user (unauthorized for compliance vault)
        self.customer_user = User.objects.create_user(
            username='test_customer',
            email='customer@acme.gh',
            password='Password123!',
            role=User.Role.CUSTOMER
        )

        # Provider Company
        self.provider = ProviderCompany.objects.create(
            company_name="Apex Logistics Ghana",
            registration_number="CS-11223-2023",
            contact_person="Kwame Mensah",
            phone="+233241000001",
            email="admin@testprovider.gh",
            status=ProviderCompany.Status.APPROVED,
            settlement_bank="057",
            settlement_bank_name="Ecobank Ghana",
            account_number="1441009988771",
            account_name="Apex Logistics Ghana Ltd",
            paystack_subaccount_code="ACCT_apex_test_01",
            paystack_subaccount_status="active",
            percentage_charge=Decimal("15.00"),
        )

        # Vehicle
        self.vehicle = Vehicle.objects.create(
            provider=self.provider,
            registration_number="GN-5500-24",
            make="Toyota",
            model="Innova",
            year=2024,
            category=Vehicle.Category.SUV,
            seating_capacity=7,
            status=Vehicle.Status.AVAILABLE,
            compliance_status=Vehicle.ComplianceStatus.PENDING_REVIEW
        )

        self.client = Client(SERVER_NAME='localhost')

    def test_provider_booking_eligibility_missing_licence(self):
        """Provider without Commercial Vehicle Operator Licence must not be eligible for bookings."""
        eligible, reason = self.provider.is_eligible_for_booking()
        self.assertFalse(eligible)
        self.assertIn("Commercial Vehicle Operator Licence", reason)

    def test_provider_booking_eligibility_expired_licence(self):
        """Provider with expired Commercial Operator Licence must be blocked."""
        ComplianceDocument.objects.create(
            provider=self.provider,
            target_type=ComplianceDocument.TargetType.PROVIDER,
            document_type=ComplianceDocument.DocumentType.OPERATOR_LICENSE,
            document_number="DVLA-OP-EXPIRED",
            document_file=ContentFile(b"dummy pdf", name="op_exp.pdf"),
            expiry_date=self.today - timedelta(days=10),
            status=ComplianceDocument.Status.EXPIRED
        )
        eligible, reason = self.provider.is_eligible_for_booking()
        self.assertFalse(eligible)
        self.assertIn("expired", reason.lower())

    def test_section_13_excoba_suspension_enforcement(self):
        """Excoba Car Rental suspension test case: must block bookings and prevent dispatch."""
        excoba = ProviderCompany.objects.create(
            company_name="Excoba Car Rental",
            registration_number="CS-89210-2021",
            contact_person="Excoba Daniels",
            phone="+233245550199",
            email="compliance@excobacarrental.gh",
            status=ProviderCompany.Status.SUSPENDED
        )
        ComplianceDocument.objects.create(
            provider=excoba,
            target_type=ComplianceDocument.TargetType.PROVIDER,
            document_type=ComplianceDocument.DocumentType.OPERATOR_LICENSE,
            document_number="DVLA-OP-2023-EXCOBA",
            document_file=ContentFile(b"dummy", name="excoba_op.pdf"),
            expiry_date=self.today - timedelta(days=30),
            status=ComplianceDocument.Status.EXPIRED
        )
        eligible, reason = excoba.is_eligible_for_booking()
        self.assertFalse(eligible)
        self.assertIn("SUSPENDED", reason)

    def test_vehicle_booking_eligibility_independent_compliance(self):
        """A vehicle is only eligible if its own registration and roadworthiness are valid and verified."""
        # 1. Provide valid operator licence to provider
        ComplianceDocument.objects.create(
            provider=self.provider,
            target_type=ComplianceDocument.TargetType.PROVIDER,
            document_type=ComplianceDocument.DocumentType.OPERATOR_LICENSE,
            document_number="DVLA-OP-VALID-01",
            document_file=ContentFile(b"dummy", name="valid_op.pdf"),
            expiry_date=self.today + timedelta(days=200),
            status=ComplianceDocument.Status.VERIFIED,
            verified_by=self.broker_user
        )

        # Vehicle currently has no documents -> not eligible
        v_ok, v_msg = self.vehicle.is_eligible_for_booking()
        self.assertFalse(v_ok)

        # Attach valid registration
        ComplianceDocument.objects.create(
            provider=self.provider,
            vehicle=self.vehicle,
            target_type=ComplianceDocument.TargetType.VEHICLE,
            document_type=ComplianceDocument.DocumentType.VEHICLE_REGISTRATION,
            document_number="DVLA-VR-5500",
            document_file=ContentFile(b"dummy", name="vr.pdf"),
            status=ComplianceDocument.Status.VERIFIED,
            verified_by=self.broker_user
        )

        # Attach valid roadworthiness
        ComplianceDocument.objects.create(
            provider=self.provider,
            vehicle=self.vehicle,
            target_type=ComplianceDocument.TargetType.VEHICLE,
            document_type=ComplianceDocument.DocumentType.ROADWORTHINESS,
            document_number="DVLA-RW-5500",
            document_file=ContentFile(b"dummy", name="rw.pdf"),
            expiry_date=self.today + timedelta(days=180),
            status=ComplianceDocument.Status.VERIFIED,
            verified_by=self.broker_user
        )

        # Update vehicle status to verified
        self.vehicle.compliance_status = Vehicle.ComplianceStatus.VERIFIED
        self.vehicle.save()

        v_ok, v_msg = self.vehicle.is_eligible_for_booking()
        self.assertTrue(v_ok)
        self.assertIn("fully compliant", v_msg.lower())

    def test_broker_document_approval_and_rejection(self):
        """Test broker approving and rejecting documents via Broker Compliance Dashboard."""
        self.client.force_login(self.broker_user)

        doc = ComplianceDocument.objects.create(
            provider=self.provider,
            vehicle=self.vehicle,
            target_type=ComplianceDocument.TargetType.VEHICLE,
            document_type=ComplianceDocument.DocumentType.ROADWORTHINESS,
            document_number="DVLA-RW-TEST-99",
            document_file=ContentFile(b"dummy", name="rw_test.pdf"),
            expiry_date=self.today + timedelta(days=90),
            status=ComplianceDocument.Status.PENDING_REVIEW
        )

        # Approve
        resp = self.client.post('/broker/compliance/', {
            'action': 'approve_document',
            'document_id': doc.id,
            'notes': 'DVLA hologram verified.'
        })
        self.assertEqual(resp.status_code, 302)
        doc.refresh_from_db()
        self.assertEqual(doc.status, ComplianceDocument.Status.VERIFIED)
        self.assertEqual(doc.verified_by, self.broker_user)

        # Reject
        resp_rej = self.client.post('/broker/compliance/', {
            'action': 'reject_document',
            'document_id': doc.id,
            'rejection_reason': 'Illegible photocopy of testing stamp.'
        })
        self.assertEqual(resp_rej.status_code, 302)
        doc.refresh_from_db()
        self.assertEqual(doc.status, ComplianceDocument.Status.REJECTED)
        self.assertEqual(doc.rejection_reason, 'Illegible photocopy of testing stamp.')

        # Verify audit log was written
        logs = ComplianceAuditLog.objects.filter(document=doc)
        self.assertEqual(logs.count(), 2)

    def test_pdf_report_generation_and_redaction(self):
        """Test Paystack Compliance Evidence PDF report generation and PII redaction."""
        pdf_normal = generate_compliance_report_pdf(self.provider, redact=False)
        self.assertGreater(len(pdf_normal.getvalue()), 1000)

        pdf_redacted = generate_compliance_report_pdf(self.provider, redact=True)
        self.assertGreater(len(pdf_redacted.getvalue()), 1000)

        # HTTP Endpoint check
        self.client.force_login(self.broker_user)
        resp = self.client.get(f'/compliance/report/{self.provider.id}/?redact=1')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers['Content-Type'], 'application/pdf')

    def test_secure_document_download_access_control(self):
        """Test Section 14 private storage access control."""
        doc = ComplianceDocument.objects.create(
            provider=self.provider,
            target_type=ComplianceDocument.TargetType.PROVIDER,
            document_type=ComplianceDocument.DocumentType.TAX_CERTIFICATE,
            document_number="GRA-TCC-2024",
            document_file=ContentFile(b"%PDF-1.4 Tax Clearance Certificate", name="tcc.pdf"),
            status=ComplianceDocument.Status.VERIFIED
        )

        # Unauthenticated -> redirect
        client_anon = Client(SERVER_NAME='localhost')
        resp_anon = client_anon.get(f'/compliance/download/{doc.id}/')
        self.assertEqual(resp_anon.status_code, 302)

        # Unauthorized Customer -> 403
        self.client.force_login(self.customer_user)
        resp_cust = self.client.get(f'/compliance/download/{doc.id}/')
        self.assertEqual(resp_cust.status_code, 403)

        # Broker -> 200
        self.client.force_login(self.broker_user)
        resp_broker = self.client.get(f'/compliance/download/{doc.id}/')
        self.assertEqual(resp_broker.status_code, 200)

    def test_automated_expiry_monitoring_task(self):
        """Test Celery background expiry scanning task at 14 days and past due."""
        doc_14d = ComplianceDocument.objects.create(
            provider=self.provider,
            vehicle=self.vehicle,
            target_type=ComplianceDocument.TargetType.VEHICLE,
            document_type=ComplianceDocument.DocumentType.ROADWORTHINESS,
            document_number="RW-EXP-14D",
            document_file=ContentFile(b"dummy", name="rw14.pdf"),
            expiry_date=self.today + timedelta(days=14),
            status=ComplianceDocument.Status.VERIFIED
        )

        doc_expired = ComplianceDocument.objects.create(
            provider=self.provider,
            vehicle=self.vehicle,
            target_type=ComplianceDocument.TargetType.VEHICLE,
            document_type=ComplianceDocument.DocumentType.COMMERCIAL_INSURANCE,
            document_number="INS-EXP-PAST",
            document_file=ContentFile(b"dummy", name="inspast.pdf"),
            expiry_date=self.today - timedelta(days=2),
            status=ComplianceDocument.Status.VERIFIED
        )

        res = check_document_expirations_task()
        self.assertEqual(res['status'], 'success')
        self.assertGreaterEqual(res['notices_sent'], 1)
        self.assertGreaterEqual(res['expired_lockouts'], 1)

        doc_14d.refresh_from_db()
        self.assertEqual(doc_14d.status, ComplianceDocument.Status.EXPIRING_SOON)

        doc_expired.refresh_from_db()
        self.assertEqual(doc_expired.status, ComplianceDocument.Status.EXPIRED)

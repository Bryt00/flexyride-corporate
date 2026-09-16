from datetime import timedelta, date
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal

from accounts.models import User, CorporateCustomer, ProviderCompany
from bookings.models import TransportationRequest, RecurringSchedule, PassengerInfo, VehicleAssignment
from fleet.models import Vehicle, Driver
from compliance.models import ComplianceDocument
from quotations.models import ProviderQuoteRequest
from bookings.tasks import generate_recurring_bookings_task
from compliance.tasks import check_document_expirations_task
from sla.tasks import detect_sla_breaches_task


class ScheduledTasksTestCase(TestCase):
    def setUp(self):
        self.customer = CorporateCustomer.objects.create(
            company_name="Test Enterprise Inc",
            contact_email="test@enterprise.com",
            contact_phone="+233241112222"
        )
        self.user = User.objects.create_user(
            username="requester1",
            email="req@enterprise.com",
            password="password123",
            role=User.Role.CUSTOMER
        )
        self.provider = ProviderCompany.objects.create(
            company_name="Gold Coast Shuttles",
            contact_person="Kofi Boateng",
            phone="+233240001122",
            email="dispatch@goldcoast.com"
        )
        self.vehicle = Vehicle.objects.create(
            provider=self.provider,
            make="Toyota",
            model="Land Cruiser Prado",
            registration_number="GS 9911-24",
            seating_capacity=5,
            category=Vehicle.Category.SUV
        )
        self.driver = Driver.objects.create(
            provider=self.provider,
            full_name="Kwame Asare",
            phone_number="+233240003344",
            license_number="DL-991122"
        )

    def test_recurring_bookings_generation(self):
        today = timezone.now().date()
        template_req = TransportationRequest.objects.create(
            customer=self.customer,
            requester=self.user,
            request_number="FRC-TEMPL-01",
            journey_type='ONE_WAY',
            pickup_address="Accra Mall",
            destination_address="Airport Terminal 3",
            departure_datetime=timezone.now() + timedelta(days=1),
            booking_status=TransportationRequest.BookingStatus.CONFIRMED
        )
        PassengerInfo.objects.create(
            request=template_req,
            full_name="Executive Passenger",
            phone_number="+233241234567"
        )

        schedule = RecurringSchedule.objects.create(
            request=template_req,
            frequency=RecurringSchedule.Frequency.DAILY,
            days_of_week="MON,TUE,WED,THU,FRI,SAT,SUN",
            start_date=today,
            end_date=today + timedelta(days=5)
        )

        res = generate_recurring_bookings_task(days_ahead=3)
        self.assertEqual(res['status'], 'success')
        self.assertGreaterEqual(res['generated_count'], 1)

    def test_compliance_document_expiration_and_lockout(self):
        today = timezone.now().date()
        # Expired document
        expired_doc = ComplianceDocument.objects.create(
            target_type=ComplianceDocument.TargetType.VEHICLE,
            document_type=ComplianceDocument.DocumentType.ROADWORTHINESS,
            vehicle=self.vehicle,
            expiry_date=today - timedelta(days=2),
            status=ComplianceDocument.Status.APPROVED
        )

        res = check_document_expirations_task()
        self.assertEqual(res['status'], 'success')
        expired_doc.refresh_from_db()
        self.assertEqual(expired_doc.status, ComplianceDocument.Status.EXPIRED)

    def test_sla_breach_detection(self):
        req = TransportationRequest.objects.create(
            customer=self.customer,
            requester=self.user,
            request_number="FRC-SLA-01",
            journey_type='ONE_WAY',
            pickup_address="Cantonments",
            destination_address="Ridge",
            departure_datetime=timezone.now() + timedelta(hours=5),
            booking_status=TransportationRequest.BookingStatus.RECEIVED_BY_FLEXYRIDE
        )
        pqr = ProviderQuoteRequest.objects.create(
            request=req,
            provider=self.provider,
            status=ProviderQuoteRequest.Status.SENT
        )
        # Mock requested_at to 3 hours ago
        ProviderQuoteRequest.objects.filter(id=pqr.id).update(
            requested_at=timezone.now() - timedelta(hours=3)
        )

        res = detect_sla_breaches_task()
        self.assertEqual(res['status'], 'success')
        self.assertGreaterEqual(res['breaches_detected'], 1)

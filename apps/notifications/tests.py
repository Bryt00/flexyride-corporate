from decimal import Decimal
from django.test import TestCase
from django.core import mail
from django.utils import timezone

from accounts.models import User, CorporateCustomer, ProviderCompany
from fleet.models import Vehicle, Driver
from bookings.models import TransportationRequest, PassengerInfo, VehicleAssignment
from quotations.models import CustomerQuote
from payments.models import PaymentTransaction, PaymentReceipt
from notifications.models import Notification
from notifications.email_service import (
    send_quote_ready_email,
    send_booking_confirmation_email,
    send_payment_receipt_email,
    send_driver_assigned_email,
)
from notifications.tasks import (
    send_quote_ready_email_async,
    send_booking_confirmation_email_async,
    send_payment_receipt_email_async,
    send_driver_assigned_email_async,
)


class NotificationEmailServiceTests(TestCase):
    def setUp(self):
        # 1. Customer User and Company
        self.customer_user = User.objects.create_user(
            username='corp_rep',
            email='rep@corporate.com',
            role=User.Role.CUSTOMER,
            password='TestPassword123!'
        )
        self.company = CorporateCustomer.objects.create(
            company_name='Enterprise Global GH',
            contact_email='contact@enterprise.com',
            contact_phone='+233 24 000 1111',
            status=CorporateCustomer.Status.APPROVED
        )

        # 2. Provider and Fleet
        self.provider = ProviderCompany.objects.create(
            company_name='Accra Executive Fleet',
            registration_number='DVLA-GH-001',
            contact_person='Kwame Asare',
            phone='+233 20 111 3333',
            email='dispatch@accrafleet.gh'
        )
        self.driver = Driver.objects.create(
            provider=self.provider,
            full_name='Emmanuel Mensah',
            license_number='GH-DRV-9988',
            phone_number='+233 24 555 7777',
            status=Driver.Status.AVAILABLE
        )
        self.vehicle = Vehicle.objects.create(
            provider=self.provider,
            make='Mercedes-Benz',
            model='E-Class Executive',
            registration_number='GT-4488-24',
            category=Vehicle.Category.EXECUTIVE,
            status=Vehicle.Status.AVAILABLE
        )

        # 3. Transportation Request
        self.req = TransportationRequest.objects.create(
            request_number='FRC-TEST-0001',
            customer=self.company,
            requester=self.customer_user,
            pickup_address='Kotoka International Airport Terminal 3, Accra',
            destination_address='Kempinski Hotel Gold Coast City, Accra',
            departure_datetime=timezone.now() + timezone.timedelta(days=1),
            requested_vehicle_category='EXECUTIVE',
            passenger_count=2,
            booking_status=TransportationRequest.BookingStatus.QUOTE_AVAILABLE
        )

        # 4. Primary Passenger
        self.passenger = PassengerInfo.objects.create(
            request=self.req,
            full_name='Dr. Grace Kusi',
            phone_number='+233 24 999 8888',
            email='grace.kusi@enterprise.com',
            is_primary=True
        )

        # 5. Customer Quote
        self.quote = CustomerQuote.objects.create(
            request=self.req,
            provider_cost=Decimal('700.00'),
            margin_amount=Decimal('150.00'),
            final_customer_price=Decimal('850.00'),
            status=CustomerQuote.Status.SENT,
            created_by=self.customer_user
        )

        # 6. Payment Transaction
        self.payment = PaymentTransaction.objects.create(
            request=self.req,
            customer_quote=self.quote,
            amount=Decimal('850.00'),
            currency='GHS',
            payment_method=PaymentTransaction.PaymentMethod.MOBILE_MONEY,
            transaction_reference='PAY-TEST-9999',
            gateway_reference='PAYSTACK-GW-001',
            status=PaymentTransaction.Status.SUCCESSFUL,
            paid_by=self.customer_user,
            payment_date=timezone.now()
        )
        self.receipt, _ = PaymentReceipt.objects.get_or_create(
            transaction=self.payment,
            defaults={'receipt_number': 'RCT-TEST-0001'}
        )

    def test_send_quote_ready_email_sync(self):
        """Verify quote ready transactional email is sent with audit trail."""
        mail.outbox = []
        result = send_quote_ready_email(self.quote, self.req, async_send=False)
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn("Quote Ready: Transfer #FRC-TEST-0001", sent.subject)
        self.assertIn("850.00", sent.subject)
        self.assertEqual(sent.to, ['rep@corporate.com'])
        self.assertTrue(any("text/html" in alt[1] for alt in sent.alternatives))

        # Check DB audit log
        notif = Notification.objects.filter(
            request=self.req,
            channel=Notification.Channel.EMAIL,
            notification_type=Notification.NotificationType.QUOTE_READY
        ).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.delivery_status, Notification.DeliveryStatus.SENT)

    def test_send_booking_confirmation_email_sync(self):
        """Verify booking confirmation transactional email is sent with audit trail."""
        mail.outbox = []
        result = send_booking_confirmation_email(self.req, self.quote, self.payment, async_send=False)
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn("Booking Confirmed: Transfer #FRC-TEST-0001", sent.subject)
        self.assertEqual(sent.to, ['rep@corporate.com'])
        self.assertIn("Kotoka International Airport", sent.body)

        # Check DB audit log
        notif = Notification.objects.filter(
            request=self.req,
            channel=Notification.Channel.EMAIL,
            notification_type=Notification.NotificationType.BOOKING_UPDATE
        ).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.delivery_status, Notification.DeliveryStatus.SENT)

    def test_send_payment_receipt_email_sync(self):
        """Verify itemized payment receipt email is sent with audit trail."""
        mail.outbox = []
        result = send_payment_receipt_email(self.payment, self.receipt, async_send=False)
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn(f"Payment Receipt #{self.receipt.receipt_number}", sent.subject)
        self.assertIn("850.00", sent.subject)
        self.assertEqual(sent.to, ['rep@corporate.com'])

        # Check DB audit log
        notif = Notification.objects.filter(
            request=self.req,
            channel=Notification.Channel.EMAIL,
            notification_type=Notification.NotificationType.PAYMENT_CONFIRMED
        ).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.delivery_status, Notification.DeliveryStatus.SENT)

    def test_send_driver_assigned_email_sync(self):
        """Verify chauffeur assignment email is dispatched to passenger and requester."""
        assignment = VehicleAssignment.objects.create(
            request=self.req,
            vehicle=self.vehicle,
            driver=self.driver,
            status=VehicleAssignment.Status.ASSIGNED
        )
        mail.outbox = []
        result = send_driver_assigned_email(assignment, async_send=False)
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn("Driver Assigned: Transfer #FRC-TEST-0001", sent.subject)
        self.assertIn("Emmanuel Mensah", sent.subject)
        self.assertIn('grace.kusi@enterprise.com', sent.to)
        self.assertIn('rep@corporate.com', sent.to)

        # Check DB audit log
        notif = Notification.objects.filter(
            request=self.req,
            channel=Notification.Channel.EMAIL,
            notification_type=Notification.NotificationType.DRIVER_ASSIGNED
        ).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.delivery_status, Notification.DeliveryStatus.SENT)

    def test_payment_signal_idempotent_email_dispatch(self):
        """Verify payment signal automatically dispatches receipt and confirmation without duplicate spam."""
        mail.outbox = []
        # Clear out existing email notifications for this request
        Notification.objects.filter(request=self.req, channel=Notification.Channel.EMAIL).delete()

        # Trigger save
        self.payment.status = PaymentTransaction.Status.SUCCESSFUL
        self.payment.save()

        # Should have sent 2 emails: receipt and booking confirmation
        self.assertEqual(len(mail.outbox), 2)

        # Trigger second save - should be idempotent and not send duplicates
        self.payment.save()
        self.assertEqual(len(mail.outbox), 2)

    def test_celery_tasks_execution(self):
        """Verify that Celery worker shared tasks execute and deliver emails."""
        mail.outbox = []
        # Test quote Celery task
        send_quote_ready_email_async.apply(args=[self.quote.id, self.req.id])
        self.assertGreaterEqual(len(mail.outbox), 1)

        # Test booking confirmation Celery task
        mail.outbox = []
        send_booking_confirmation_email_async.apply(args=[self.req.id, self.quote.id, self.payment.id])
        self.assertEqual(len(mail.outbox), 1)

        # Test payment receipt Celery task
        mail.outbox = []
        send_payment_receipt_email_async.apply(args=[self.payment.id, self.receipt.id])
        self.assertEqual(len(mail.outbox), 1)

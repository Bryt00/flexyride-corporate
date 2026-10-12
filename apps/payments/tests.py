from decimal import Decimal
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from accounts.models import User, ProviderCompany, CorporateCustomer, CompanyEmployee
from bookings.models import TransportationRequest, PassengerInfo
from fleet.models import VehicleCategoryRate
from quotations.models import ProviderQuoteRequest, ProviderQuote, CustomerQuote
from payments.models import PaymentTransaction
from payments import paystack


class PaystackSplitCheckoutTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Customer User and Corporate Company
        self.customer_user = User.objects.create_user(
            username='corp_pay_user',
            email='pay_user@apexenergy.gh',
            role=User.Role.CUSTOMER,
            password='TestPassword123!'
        )
        self.corporate_company = CorporateCustomer.objects.create(
            company_name='Apex Energy Ghana Ltd',
            contact_email='pay_user@apexenergy.gh',
            contact_phone='+233 30 211 0000',
            status=CorporateCustomer.Status.APPROVED,
            preferred_currency='GHS'
        )
        CompanyEmployee.objects.create(
            company=self.corporate_company,
            user=self.customer_user,
            can_approve_requests=True
        )

        # 2. Provider with Paystack Subaccount
        self.provider_with_subacc = ProviderCompany.objects.create(
            company_name='Goldstar VIP Transit',
            registration_number='DVLA-GH-COMM-888',
            contact_person='Kofi Mensah',
            phone='+233 24 111 2222',
            email='dispatch@goldstar.gh',
            address='10 Independence Ave, Accra',
            status=ProviderCompany.Status.APPROVED,
            overall_rating=Decimal('4.90'),
            service_area='Greater Accra, Tema',
            paystack_subaccount_code='ACCT_gh_goldstar_888',
            payout_channel='BANK',
            settlement_bank='040100',
            settlement_bank_name='GCB Bank Limited',
            account_number='1010101010101',
            account_name='Goldstar VIP Transit Ltd'
        )

        # 3. Provider WITHOUT Subaccount
        self.provider_without_subacc = ProviderCompany.objects.create(
            company_name='Silverline Express',
            registration_number='DVLA-GH-COMM-777',
            contact_person='Ama Serwaa',
            phone='+233 24 333 4444',
            email='dispatch@silverline.gh',
            address='25 Cantonments Rd, Accra',
            status=ProviderCompany.Status.APPROVED,
            overall_rating=Decimal('4.80'),
            service_area='Greater Accra'
        )

        # 4. Transportation Request
        self.trip_request = TransportationRequest.objects.create(
            request_number='FRC-20261008-0001',
            customer=self.corporate_company,
            requester=self.customer_user,
            journey_type='ONE_WAY',
            pickup_address='Ridge, Accra',
            destination_address='Tema Port, Greater Accra',
            departure_datetime=timezone.now() + timezone.timedelta(days=1),
            requested_vehicle_category='EXECUTIVE',
            passenger_count=2,
            booking_status=TransportationRequest.BookingStatus.QUOTE_AVAILABLE
        )

        # Broker user to create CustomerQuote
        self.broker_user = User.objects.create_user(
            username='broker_pricing',
            email='broker@flexyride.com',
            role=User.Role.BROKER,
            is_staff=True,
            password='TestPassword123!'
        )

        # 5. Quotes Setup for provider with subaccount
        self.pqr = ProviderQuoteRequest.objects.create(
            request=self.trip_request,
            provider=self.provider_with_subacc,
            status=ProviderQuoteRequest.Status.RESPONDED
        )
        self.pq = ProviderQuote.objects.create(
            quote_request=self.pqr,
            provider=self.provider_with_subacc,
            offered_cost=Decimal('1000.00'),
            status=ProviderQuote.Status.ACCEPTED_BY_BROKER
        )
        self.cq = CustomerQuote.objects.create(
            request=self.trip_request,
            selected_provider_quote=self.pq,
            provider_cost=Decimal('1000.00'),
            margin_amount=Decimal('250.00'),
            final_customer_price=Decimal('1250.00'),
            status=CustomerQuote.Status.SENT,
            created_by=self.broker_user
        )

    def test_payment_view_context_with_provider_subaccount(self):
        """Verify checkout view injects provider's Paystack subaccount and platform margin."""
        self.client.login(username='corp_pay_user', password='TestPassword123!')
        url = reverse('portal_payment', kwargs={'request_id': self.trip_request.request_number})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Context assertions
        self.assertEqual(response.context['paystack_subaccount_code'], 'ACCT_gh_goldstar_888')
        # margin_amount is 250.00 -> 25000 pesewas
        self.assertEqual(response.context['paystack_transaction_charge'], 25000)
        # amount_subunits is 1250.00 -> 125000 pesewas
        self.assertEqual(response.context['paystack_amount_subunits'], 125000)

        # HTML assertions
        self.assertContains(response, 'ACCT_gh_goldstar_888')

    def test_payment_view_without_subaccount(self):
        """Verify checkout safely handles providers without a configured subaccount."""
        # Switch quote to provider without subaccount
        self.pq.provider = self.provider_without_subacc
        self.pq.save()

        self.client.login(username='corp_pay_user', password='TestPassword123!')
        url = reverse('portal_payment', kwargs={'request_id': self.trip_request.request_number})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context['paystack_subaccount_code'], '')

    def test_initialize_transaction_includes_subaccount_and_charge(self):
        """Verify paystack.initialize_transaction payload includes subaccount & charge."""
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "status": True,
                "data": {
                    "authorization_url": "https://checkout.paystack.com/000abc",
                    "access_code": "000abc",
                    "reference": "TEST-REF-99"
                }
            }).encode('utf-8')
            mock_urlopen.return_value.__enter__.return_value = mock_response

            res = paystack.initialize_transaction(
                email="client@flexyride.com",
                amount_in_major=Decimal('500.00'),
                reference="TEST-REF-99",
                callback_url="https://flexyride.com/callback",
                subaccount="ACCT_split_test",
                transaction_charge=5000
            )

            self.assertTrue(res['success'])
            self.assertEqual(res['reference'], 'TEST-REF-99')

            # Verify request data sent to Paystack
            call_args = mock_urlopen.call_args
            req = call_args[0][0]
            body = json.loads(req.data.decode('utf-8'))
            self.assertEqual(body['subaccount'], 'ACCT_split_test')
            self.assertEqual(body['transaction_charge'], 5000)
            self.assertEqual(body['bearer'], 'subaccount')

    def test_verify_webhook_signature(self):
        """Verify webhook signature HMAC-SHA512 verification."""
        import hmac
        import hashlib
        secret = "test_secret_key_12345"
        payload = b'{"event": "charge.success", "data": {"reference": "PAY-1234"}}'
        computed = hmac.new(secret.encode('utf-8'), payload, hashlib.sha512).hexdigest()

        with patch.object(settings, 'PAYSTACK_SECRET_KEY', secret):
            self.assertTrue(paystack.verify_webhook_signature(payload, computed))
            self.assertFalse(paystack.verify_webhook_signature(payload, "invalid_sig"))

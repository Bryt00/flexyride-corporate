from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from accounts.models import User, CorporateCustomer, ProviderCompany
from bookings.models import TransportationRequest
from quotations.models import ProviderQuoteRequest, ProviderQuote, CustomerQuote


class QuotationsModelTests(TestCase):
    def setUp(self):
        self.customer = CorporateCustomer.objects.create(
            company_name="Corporate Client Ltd",
            contact_email="client@corp.com",
            contact_phone="+233240000000"
        )
        self.user = User.objects.create_user(
            username='rep1',
            email='rep1@corp.com',
            password='Password123!',
            role=User.Role.CUSTOMER
        )
        self.broker = User.objects.create_user(
            username='broker_staff',
            email='broker@flexyride.com',
            password='Password123!',
            role=User.Role.BROKER
        )
        self.provider = ProviderCompany.objects.create(
            company_name="Vip Cabs Ghana",
            contact_person="Sam Manager",
            phone="+233240000001",
            email="sam@vipcabs.com"
        )
        self.req = TransportationRequest.objects.create(
            customer=self.customer,
            requester=self.user,
            pickup_address="Kotoka International Airport (ACC)",
            destination_address="Kempinski Hotel Gold Coast City, Accra",
            departure_datetime=timezone.now()
        )

    def test_provider_quote_and_customer_quote_margin_calculation(self):
        p_req = ProviderQuoteRequest.objects.create(
            request=self.req,
            provider=self.provider
        )
        p_quote = ProviderQuote.objects.create(
            quote_request=p_req,
            provider=self.provider,
            offered_cost=Decimal("150000.00")
        )
        
        c_quote = CustomerQuote.objects.create(
            request=self.req,
            selected_provider_quote=p_quote,
            provider_cost=Decimal("150000.00"),
            final_customer_price=Decimal("200000.00"),
            created_by=self.broker
        )

        # Margin should be automatically calculated as final_customer_price - provider_cost
        self.assertEqual(c_quote.margin_amount, Decimal("50000.00"))
        self.assertEqual(c_quote.calculate_margin(), Decimal("50000.00"))

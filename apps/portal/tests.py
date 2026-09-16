from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, ProviderCompany, CorporateCustomer, CompanyEmployee
from fleet.models import Vehicle, Driver
from bookings.models import TransportationRequest, PassengerInfo
from quotations.models import ProviderQuoteRequest, ProviderQuote


class BrokerProviderCRUDTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create Broker User
        self.broker_user = User.objects.create_user(
            username='broker_ops',
            email='broker@flexyride.com',
            role=User.Role.BROKER,
            is_staff=True,
            password='TestPassword123!'
        )
        self.client.login(username='broker_ops', password='TestPassword123!')

        # Existing Provider
        self.provider = ProviderCompany.objects.create(
            company_name='Goldstar VIP Transit',
            registration_number='DVLA-GH-COMM-999',
            contact_person='Kofi Mensah',
            phone='+233 24 111 2222',
            email='dispatch@goldstar.gh',
            address='10 Independence Ave, Accra',
            status=ProviderCompany.Status.APPROVED,
            overall_rating=Decimal('4.90'),
            service_area='Greater Accra, Tema',
        )
        # Customer setup for request creation tests
        self.customer_user = User.objects.create_user(
            username='corporate_requester',
            email='procurement@apexenergy.gh',
            role=User.Role.CUSTOMER,
            password='TestPassword123!'
        )
        self.corporate_company = CorporateCustomer.objects.create(
            company_name='Apex Energy Ghana Ltd',
            contact_email='procurement@apexenergy.gh',
            contact_phone='+233 30 211 0000',
            status=CorporateCustomer.Status.APPROVED,
            preferred_currency='GHS'
        )
        CompanyEmployee.objects.create(
            company=self.corporate_company,
            user=self.customer_user,
            can_approve_requests=True
        )

    def test_broker_providers_view_get(self):
        """Verify broker can access the transport provider network page."""
        response = self.client.get(reverse('portal_broker_providers'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Goldstar VIP Transit')
        self.assertContains(response, 'DVLA-GH-COMM-999')
        self.assertContains(response, 'Onboard Provider')

    def test_broker_providers_filtering(self):
        """Test status filtering and text search query."""
        # Create a pending provider
        ProviderCompany.objects.create(
            company_name='Kumasi Express Shuttles',
            registration_number='DVLA-GH-KS-101',
            contact_person='Ama Serwaa',
            phone='+233 20 333 4444',
            email='ama@kumasishuttle.gh',
            status=ProviderCompany.Status.PENDING
        )

        # Filter by APPROVED
        res_approved = self.client.get(reverse('portal_broker_providers') + '?status=APPROVED')
        self.assertEqual(res_approved.status_code, 200)
        self.assertContains(res_approved, 'Goldstar VIP Transit')
        self.assertNotContains(res_approved, 'Kumasi Express Shuttles')

        # Filter by PENDING
        res_pending = self.client.get(reverse('portal_broker_providers') + '?status=PENDING')
        self.assertEqual(res_pending.status_code, 200)
        self.assertContains(res_pending, 'Kumasi Express Shuttles')
        self.assertNotContains(res_pending, 'Goldstar VIP Transit')

        # Search query
        res_search = self.client.get(reverse('portal_broker_providers') + '?q=Goldstar')
        self.assertContains(res_search, 'Goldstar VIP Transit')
        self.assertNotContains(res_search, 'Kumasi Express Shuttles')

    def test_onboard_provider_with_admin_account(self):
        """Test onboarding a new transport provider with auto-provisioned admin account."""
        post_data = {
            'action': 'onboard_provider',
            'company_name': 'Apex Prestige Fleets',
            'registration_number': 'DVLA-GH-COMM-777',
            'contact_person': 'Kwesi Arthur',
            'phone': '+233 24 555 6677',
            'email': 'dispatch@apexprestige.gh',
            'address': 'Plot 12 Airport City, Accra',
            'service_area': 'Accra, Takoradi, Kumasi',
            'specializations': 'Executive SUV, Coaster Bus',
            'status': 'APPROVED',
            'overall_rating': '5.0',
            'create_admin_account': 'true',
            'admin_username': 'apex_dispatcher',
            'admin_password': 'ApexSecret2026!'
        }
        response = self.client.post(reverse('portal_broker_providers'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify company created
        new_provider = ProviderCompany.objects.filter(email='dispatch@apexprestige.gh').first()
        self.assertIsNotNone(new_provider)
        self.assertEqual(new_provider.company_name, 'Apex Prestige Fleets')
        self.assertEqual(new_provider.status, ProviderCompany.Status.APPROVED)
        self.assertEqual(new_provider.registration_number, 'DVLA-GH-COMM-777')

        # Verify Provider Admin user created
        user = User.objects.filter(username='apex_dispatcher').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'dispatch@apexprestige.gh')
        self.assertEqual(user.role, User.Role.PROVIDER_ADMIN)
        self.assertTrue(user.is_verified)
        self.assertTrue(user.check_password('ApexSecret2026!'))

    def test_update_provider(self):
        """Test editing an existing transport provider company."""
        post_data = {
            'action': 'update_provider',
            'provider_id': self.provider.id,
            'company_name': 'Goldstar VIP Global Logistics',
            'registration_number': 'DVLA-GH-COMM-999-REV',
            'contact_person': 'Kofi Mensah Snr',
            'phone': '+233 24 999 8888',
            'email': 'operations@goldstar.gh',
            'address': '55 Ring Road Central, Accra',
            'service_area': 'All Regions, Ghana',
            'specializations': 'VIP Chauffeuring, Armored Vehicles',
            'status': 'APPROVED',
            'overall_rating': '5.00'
        }
        response = self.client.post(reverse('portal_broker_providers'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        self.provider.refresh_from_db()
        self.assertEqual(self.provider.company_name, 'Goldstar VIP Global Logistics')
        self.assertEqual(self.provider.registration_number, 'DVLA-GH-COMM-999-REV')
        self.assertEqual(self.provider.contact_person, 'Kofi Mensah Snr')
        self.assertEqual(self.provider.phone, '+233 24 999 8888')
        self.assertEqual(self.provider.email, 'operations@goldstar.gh')
        self.assertEqual(self.provider.service_area, 'All Regions, Ghana')

    def test_toggle_provider_status(self):
        """Test toggling provider status between APPROVED and SUSPENDED."""
        # 1. Suspend
        post_data = {
            'action': 'toggle_provider_status',
            'provider_id': self.provider.id,
            'new_status': 'SUSPENDED'
        }
        res = self.client.post(reverse('portal_broker_providers'), post_data, follow=True)
        self.assertEqual(res.status_code, 200)
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.status, ProviderCompany.Status.SUSPENDED)

        # 2. Re-approve
        post_data['new_status'] = 'APPROVED'
        res2 = self.client.post(reverse('portal_broker_providers'), post_data, follow=True)
        self.assertEqual(res2.status_code, 200)
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.status, ProviderCompany.Status.APPROVED)

    def test_delete_provider_soft_suspend_when_records_exist(self):
        """Verify provider is soft-suspended when linked vehicles or quotes exist."""
        # Create a linked vehicle
        Vehicle.objects.create(
            provider=self.provider,
            make='Toyota',
            model='Land Cruiser Prado',
            year=2024,
            registration_number='GE-4040-24',
            category=Vehicle.Category.SUV,
            seating_capacity=5
        )

        post_data = {
            'action': 'delete_provider',
            'provider_id': self.provider.id
        }
        response = self.client.post(reverse('portal_broker_providers'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Provider should still exist, but status changed to SUSPENDED
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.status, ProviderCompany.Status.SUSPENDED)

    def test_delete_empty_provider_hard_delete(self):
        """Verify an empty provider without linked records is permanently removed."""
        empty_provider = ProviderCompany.objects.create(
            company_name='Test Empty Transit',
            contact_person='Test Person',
            phone='+233 20 000 0000',
            email='empty@transit.gh'
        )
        empty_id = empty_provider.id

        post_data = {
            'action': 'delete_provider',
            'provider_id': empty_id
        }
        response = self.client.post(reverse('portal_broker_providers'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Should be deleted
        self.assertFalse(ProviderCompany.objects.filter(id=empty_id).exists())

    def test_broadcast_rfq_verified_query_fix(self):
        """Test broadcast_rfq correctly queries ProviderCompany by status=APPROVED without FieldError."""
        # Create a corporate customer and request
        customer = CorporateCustomer.objects.create(
            company_name='MTN Ghana HQ',
            contact_email='procurement@mtn.com.gh',
            contact_phone='+233 30 200 1234'
        )
        req = TransportationRequest.objects.create(
            customer=customer,
            requester=self.broker_user,
            journey_type=TransportationRequest.JourneyType.AIRPORT_TRANSFER,
            pickup_address='Terminal 3, Kotoka International Airport',
            destination_address='MTN House, Ridge, Accra',
            departure_datetime=timezone.now() + timezone.timedelta(days=2),
            requested_vehicle_category='SUV'
        )

        post_data = {
            'action': 'broadcast_rfq',
            'request_id': req.id
        }
        response = self.client.post(reverse('portal_broker_rfqs'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify quote request was created for approved provider
        pqr = ProviderQuoteRequest.objects.filter(request=req, provider=self.provider).first()
        self.assertIsNotNone(pqr)
        self.assertEqual(pqr.status, 'SENT')

    def test_transport_request_submission_success(self):
        """Test corporate customer can submit a one-way transport request via wizard."""
        self.client.login(username='corporate_requester', password='TestPassword123!')
        
        dep_time = (timezone.now() + timezone.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        post_data = {
            'journey_type': 'ONE_WAY',
            'requested_vehicle_category': 'SEDAN',
            'pickup_address': 'Airport Residential Area, Accra',
            'destination_address': 'Tema Port Gate 2, Tema',
            'departure_datetime': dep_time,
            'passenger_count': 1,
            'full_name': 'Kwame Mensah',
            'phone_number': '+233 24 123 4567',
            'email': 'kwame.mensah@apexenergy.gh',
        }
        response = self.client.post(reverse('portal_new_request'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify request exists in DB
        req = TransportationRequest.objects.filter(pickup_address='Airport Residential Area, Accra').first()
        self.assertIsNotNone(req)
        self.assertEqual(req.destination_address, 'Tema Port Gate 2, Tema')
        self.assertEqual(req.customer, self.corporate_company)
        self.assertEqual(req.requester, self.customer_user)
        self.assertEqual(req.journey_type, 'ONE_WAY')
        self.assertEqual(req.requested_vehicle_category, 'SEDAN')
        self.assertEqual(req.priority_level, 'STANDARD')
        self.assertEqual(req.vehicles_requested_count, 1)

        # Verify primary passenger created
        passenger = PassengerInfo.objects.filter(request=req).first()
        self.assertIsNotNone(passenger)
        self.assertEqual(passenger.full_name, 'Kwame Mensah')
        self.assertEqual(passenger.phone_number, '+233 24 123 4567')

    def test_airport_transfer_request_submission(self):
        """Test customer submitting an airport transfer request with flight details."""
        self.client.login(username='corporate_requester', password='TestPassword123!')

        dep_time = (timezone.now() + timezone.timedelta(days=3)).strftime('%Y-%m-%dT%H:%M')
        post_data = {
            'journey_type': 'AIRPORT_TRANSFER',
            'requested_vehicle_category': 'EXECUTIVE',
            'pickup_address': 'Kotoka International Airport (ACC)',
            'destination_address': 'Kempinski Hotel Gold Coast City, Accra',
            'departure_datetime': dep_time,
            'passenger_count': 2,
            'flight_number': 'BA 078',
            'airport_name': 'Kotoka International Airport (ACC)',
            'full_name': 'Nana Ama Osei',
            'phone_number': '+233 20 888 9999',
            'email': 'nana.osei@apexenergy.gh',
        }
        response = self.client.post(reverse('portal_new_request'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        req = TransportationRequest.objects.filter(pickup_address='Kotoka International Airport (ACC)').first()
        self.assertIsNotNone(req)
        self.assertEqual(req.flight_number, 'BA 078')
        self.assertEqual(req.airport_name, 'Kotoka International Airport (ACC)')
        self.assertEqual(req.journey_type, 'AIRPORT_TRANSFER')
        self.assertEqual(req.customer, self.corporate_company)


from decimal import Decimal
from typing import cast, Any, Iterable
from django import forms
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

        # Verify automated welcome & credentials email dispatched
        from django.core import mail
        self.assertGreaterEqual(len(mail.outbox), 1)
        welcome_email = mail.outbox[-1]
        self.assertIn('dispatch@apexprestige.gh', welcome_email.to)
        self.assertIn('Welcome to FlexyRide Corporate', welcome_email.subject)
        self.assertIn('apex_dispatcher', welcome_email.body)
        self.assertIn('ApexSecret2026!', welcome_email.body)
        self.assertIn('operations@flexyridegh.com', welcome_email.from_email)
        self.assertIn('operations@flexyridegh.com', welcome_email.reply_to[0])

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

    def test_onboard_provider_with_paystack_bank_account(self):
        """Test onboarding a transport provider with bank details generates subaccount."""
        post_data = {
            'action': 'onboard_provider',
            'company_name': 'Volta Transporters Ltd',
            'registration_number': 'DVLA-GH-COMM-888',
            'contact_person': 'Elikem Kpodo',
            'phone': '+233 24 111 2233',
            'email': 'dispatch@voltatrans.gh',
            'status': 'APPROVED',
            'payout_channel': 'BANK',
            'settlement_bank': '040100',
            'settlement_bank_name': 'GCB Bank Limited',
            'account_number': '1234567890',
            'account_name': 'VOLTA TRANSPORTERS LTD',
            'percentage_charge': '5.00',
        }
        response = self.client.post(reverse('portal_broker_providers'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        provider = ProviderCompany.objects.filter(email='dispatch@voltatrans.gh').first()
        self.assertIsNotNone(provider)
        self.assertEqual(provider.payout_channel, ProviderCompany.PayoutChannel.BANK)
        self.assertEqual(provider.settlement_bank, '040100')
        self.assertEqual(provider.account_number, '1234567890')
        self.assertEqual(provider.percentage_charge, Decimal('5.00'))
        self.assertTrue(provider.has_payout_details)
        self.assertTrue(bool(provider.paystack_subaccount_code))
        self.assertTrue(provider.paystack_subaccount_code.startswith('ACCT_'))

    def test_onboard_provider_with_mobile_money(self):
        """Test onboarding a transport provider with Mobile Money settlement details."""
        post_data = {
            'action': 'onboard_provider',
            'company_name': 'Cape Coast Express',
            'registration_number': 'DVLA-GH-COMM-555',
            'contact_person': 'Kofi Annan',
            'phone': '+233 24 444 3322',
            'email': 'dispatch@capecoastexpress.gh',
            'status': 'APPROVED',
            'payout_channel': 'MOBILE_MONEY',
            'settlement_bank': 'MTN',
            'settlement_bank_name': 'MTN Mobile Money',
            'account_number': '0244443322',
            'account_name': 'CAPE COAST EXPRESS',
        }
        response = self.client.post(reverse('portal_broker_providers'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        provider = ProviderCompany.objects.filter(email='dispatch@capecoastexpress.gh').first()
        self.assertIsNotNone(provider)
        self.assertEqual(provider.payout_channel, ProviderCompany.PayoutChannel.MOBILE_MONEY)
        self.assertEqual(provider.settlement_bank, 'MTN')
        self.assertEqual(provider.account_number, '0244443322')
        self.assertTrue(bool(provider.paystack_subaccount_code))

    def test_update_provider_payout_details(self):
        """Test updating banking details on an existing approved provider."""
        post_data = {
            'action': 'update_provider',
            'provider_id': self.provider.id,
            'company_name': self.provider.company_name,
            'contact_person': self.provider.contact_person,
            'phone': self.provider.phone,
            'email': self.provider.email,
            'status': 'APPROVED',
            'payout_fields_present': '1',
            'payout_channel': 'BANK',
            'settlement_bank': '130100',
            'settlement_bank_name': 'Ecobank Ghana Limited',
            'account_number': '9876543210',
            'account_name': 'GOLDSTAR VIP LOGISTICS',
            'percentage_charge': '3.50',
        }
        response = self.client.post(reverse('portal_broker_providers'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        self.provider.refresh_from_db()
        self.assertEqual(self.provider.settlement_bank, '130100')
        self.assertEqual(self.provider.account_number, '9876543210')
        self.assertEqual(self.provider.percentage_charge, Decimal('3.50'))
        self.assertTrue(bool(self.provider.paystack_subaccount_code))

    def test_provider_portal_update_company_payout_details(self):
        """Test provider updating their own company banking details via the Provider Portal."""
        provider_user = User.objects.create_user(
            username='goldstar_admin',
            email=self.provider.email,
            role=User.Role.PROVIDER_ADMIN,
            password='ProviderPassword123!'
        )
        self.client.login(username='goldstar_admin', password='ProviderPassword123!')

        # 1. GET Provider Company Profile page - verifies Section 5 renders
        get_res = self.client.get(reverse('portal_provider_company'))
        self.assertEqual(get_res.status_code, 200)
        self.assertContains(get_res, 'Settlement Banking & Payouts')
        self.assertContains(get_res, 'payout_fields_present')

        # 2. POST update_company with banking credentials
        post_data = {
            'action': 'update_company',
            'company_name': self.provider.company_name,
            'contact_person': self.provider.contact_person,
            'phone': self.provider.phone,
            'email': self.provider.email,
            'address': self.provider.address,
            'service_area': self.provider.service_area,
            'specializations': self.provider.specializations or '',
            'payout_fields_present': '1',
            'payout_channel': 'BANK',
            'settlement_bank': '130100',
            'settlement_bank_name': 'Ecobank Ghana Limited',
            'account_number': '0241234567',
            'account_name': 'GOLDSTAR VIP TRANSIT LTD',
        }
        post_res = self.client.post(reverse('portal_provider_company'), post_data, follow=True)
        self.assertEqual(post_res.status_code, 200)

        # 3. Verify database record and automated Paystack subaccount creation
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.settlement_bank, '130100')
        self.assertEqual(self.provider.account_number, '0241234567')
        self.assertTrue(bool(self.provider.account_name))
        self.assertTrue(bool(self.provider.paystack_subaccount_code))

    def test_provider_portal_manual_sync_subaccount(self):
        """Test provider manually triggering Paystack subaccount synchronization."""
        provider_user = User.objects.create_user(
            username='goldstar_admin_sync',
            email=self.provider.email,
            role=User.Role.PROVIDER_ADMIN,
            password='ProviderPassword123!'
        )
        self.client.login(username='goldstar_admin_sync', password='ProviderPassword123!')

        # Seed banking details without subaccount code
        self.provider.settlement_bank = '130100'
        self.provider.account_number = '0241234567'
        self.provider.paystack_subaccount_code = ''
        self.provider.save(update_fields=['settlement_bank', 'account_number', 'paystack_subaccount_code'])

        post_data = {
            'action': 'sync_company_subaccount',
        }
        post_res = self.client.post(reverse('portal_provider_company'), post_data, follow=True)
        self.assertEqual(post_res.status_code, 200)

        self.provider.refresh_from_db()
        self.assertTrue(bool(self.provider.paystack_subaccount_code))

    def test_change_bank_account_preserves_subaccount_code(self):
        """Test that updating an existing provider's bank account preserves their subaccount ID."""
        # 1. Setup provider with an existing subaccount
        self.provider.settlement_bank = '040100'
        self.provider.account_number = '1111222233'
        self.provider.paystack_subaccount_code = 'ACCT_TEST_EXISTING_99'
        self.provider.save()

        original_subaccount_code = self.provider.paystack_subaccount_code

        # 2. Update to a new bank account (Absa Bank: 030100, account: 5555666677)
        post_data = {
            'action': 'update_provider',
            'provider_id': self.provider.id,
            'company_name': self.provider.company_name,
            'contact_person': self.provider.contact_person,
            'phone': self.provider.phone,
            'email': self.provider.email,
            'status': 'APPROVED',
            'payout_fields_present': '1',
            'payout_channel': 'BANK',
            'settlement_bank': '030100',
            'settlement_bank_name': 'Absa Bank Ghana Ltd',
            'account_number': '5555666677',
            'account_name': 'GOLDSTAR TRANSIT GHANA',
        }
        res = self.client.post(reverse('portal_broker_providers'), post_data, follow=True)
        self.assertEqual(res.status_code, 200)

        # 3. Refresh from DB and verify
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.settlement_bank, '030100')
        self.assertEqual(self.provider.account_number, '5555666677')
        # Crucial check: subaccount ID must remain the same!
        self.assertEqual(self.provider.paystack_subaccount_code, original_subaccount_code)

    def test_paystack_banks_api(self):
        """Test the Paystack bank directory API endpoint returns bank list."""
        response = self.client.get(reverse('portal_paystack_banks_api') + '?type=ghipss')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertIn('banks', data)
        self.assertTrue(len(data['banks']) > 0)

    def test_paystack_resolve_account_api(self):
        """Test Paystack account resolve endpoint."""
        response = self.client.get(reverse('portal_paystack_resolve_account_api') + '?account_number=1234567890&bank_code=040100')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('success', data)

    def test_fleet_categories_api(self):
        """Test the fleet categories API returns categories created by admin."""
        response = self.client.get(reverse('portal_fleet_categories_api'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertIn('categories', data)
        self.assertTrue(len(data['categories']) >= 7)
        names = [c['display_name'] for c in data['categories']]
        self.assertIn('Standard Sedan', names)
        self.assertIn('SUV / 4x4', names)
        self.assertIn('Executive Saloon', names)

    def test_provider_admin_form_specializations_dropdown(self):
        """Test ProviderCompanyAdminForm populates specializations choices with admin categories."""
        from accounts.admin import ProviderCompanyAdminForm
        form = ProviderCompanyAdminForm()
        field = form.fields['specializations']
        assert isinstance(field, forms.ChoiceField)
        choices = [c[0] for c in cast(Iterable[Any], field.choices)]
        self.assertIn('Standard Sedan', choices)
        self.assertIn('SUV / 4x4', choices)
        self.assertIn('Executive Saloon', choices)
        self.assertIn('All Fleet Categories', choices)

    def test_provider_onboarding_form_specializations_dropdown(self):
        """Test ProviderCompanyOnboardingForm populates specializations choices with admin categories."""
        from portal.forms import ProviderCompanyOnboardingForm
        form = ProviderCompanyOnboardingForm()
        field = form.fields['specializations']
        assert isinstance(field, forms.ChoiceField)
        choices = [c[0] for c in cast(Iterable[Any], field.choices)]
        self.assertIn('Standard Sedan', choices)
        self.assertIn('SUV / 4x4', choices)
        self.assertIn('Executive Saloon', choices)
        self.assertIn('All Fleet Categories', choices)

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
            pickup_address='Terminal 3, International Airport',
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

    def test_staff_member_can_create_provider(self):
        """Test any active staff member can access provider workspace and onboard providers with payout details."""
        staff_user = User.objects.create_user(
            username='staff_rep',
            email='staff@flexyride.com',
            role=User.Role.BROKER,
            is_staff=True,
            is_active=True,
            password='StaffPassword123!'
        )
        self.client.login(username='staff_rep', password='StaffPassword123!')

        # Verify staff member can view providers page
        get_res = self.client.get(reverse('portal_broker_providers'))
        self.assertEqual(get_res.status_code, 200)

        # Onboard a new provider as staff
        post_data = {
            'action': 'onboard_provider',
            'company_name': 'Volta River Shuttles',
            'registration_number': 'DVLA-GH-COMM-VOLTA',
            'contact_person': 'Akosua Mensah',
            'phone': '+233 24 333 4444',
            'email': 'dispatch@voltashuttles.gh',
            'address': 'Ho - Volta Region',
            'status': 'APPROVED',
            'payout_channel': 'BANK',
            'settlement_bank': '040100',
            'settlement_bank_name': 'GCB Bank Limited',
            'account_number': '040100987654321',
            'account_name': 'VOLTA RIVER SHUTTLES LTD',
            'percentage_charge': '5.00',
        }
        post_res = self.client.post(reverse('portal_broker_providers'), post_data, follow=True)
        self.assertEqual(post_res.status_code, 200)

        provider = ProviderCompany.objects.filter(email='dispatch@voltashuttles.gh').first()
        self.assertIsNotNone(provider)
        self.assertEqual(provider.company_name, 'Volta River Shuttles')
        self.assertEqual(provider.settlement_bank, '040100')
        self.assertEqual(provider.account_number, '040100987654321')
        self.assertEqual(provider.percentage_charge, Decimal('5.00'))
        self.assertTrue(bool(provider.paystack_subaccount_code))

    def test_deactivated_broker_or_staff_is_blocked(self):
        """Test deactivated staff or broker accounts are blocked from accessing provider creation."""
        inactive_staff = User.objects.create_user(
            username='suspended_rep',
            email='suspended@flexyride.com',
            role=User.Role.BROKER,
            is_staff=True,
            is_active=False,
            password='StaffPassword123!'
        )
        # Attempt login / session with inactive user
        self.client.force_login(inactive_staff)

        # Access should be denied (redirected to login or 302 by user_passes_test)
        get_res = self.client.get(reverse('portal_broker_providers'))
        self.assertEqual(get_res.status_code, 302)
        self.assertIn('/portal/login/', get_res.url)

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
            'pickup_address': 'International Airport',
            'destination_address': 'Kempinski Hotel Gold Coast City, Accra',
            'departure_datetime': dep_time,
            'passenger_count': 2,
            'flight_number': 'BA 078',
            'airport_name': 'International Airport',
            'full_name': 'Nana Ama Osei',
            'phone_number': '+233 20 888 9999',
            'email': 'nana.osei@apexenergy.gh',
        }
        response = self.client.post(reverse('portal_new_request'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        req = TransportationRequest.objects.filter(pickup_address='International Airport').first()
        self.assertIsNotNone(req)
        self.assertEqual(req.flight_number, 'BA 078')
        self.assertEqual(req.airport_name, 'International Airport')
        self.assertEqual(req.journey_type, 'AIRPORT_TRANSFER')
        self.assertEqual(req.customer, self.corporate_company)

    def test_fleet_categories_page_renders_with_search_bar(self):
        """Test fleet categories / marketplace page renders with vehicle search bar and filter controls."""
        response = self.client.get(reverse('portal_fleet_categories'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('fleetSearchInput', content)
        self.assertIn('Vehicle Marketplace', content)
        self.assertIn('visibleFleetCount', content)
        self.assertIn('noFleetFound', content)
        self.assertIn('Executive & VIP', content)

    def test_new_request_wizard_renders_with_consolidated_review(self):
        """Test new request wizard renders with consolidated Step 6 review cards."""
        self.client.login(username='corporate_requester', password='TestPassword123!')
        response = self.client.get(reverse('portal_new_request'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('step-content-6', content)
        self.assertIn('review-journey-type', content)
        self.assertIn('review-pickup', content)
        self.assertIn('review-dest', content)
        self.assertIn('review-passenger', content)
        self.assertIn('review-category', content)
        self.assertIn('review-badge-accessibility', content)
        self.assertIn('review-badge-executive', content)
        self.assertIn('Submit Request', content)

    def test_new_request_submission_with_special_requirements(self):
        """Test submitting a full request including accessibility and executive vehicle flags."""
        self.client.login(username='corporate_requester', password='TestPassword123!')
        dep_time = (timezone.now() + timezone.timedelta(days=2)).strftime('%Y-%m-%dT%H:%M')
        post_data = {
            'journey_type': 'ONE_WAY',
            'requested_vehicle_category': 'EXECUTIVE',
            'pickup_address': 'Ridge Hospital, Accra',
            'destination_address': 'Accra Financial Centre, Ridge',
            'departure_datetime': dep_time,
            'passenger_count': 1,
            'full_name': 'Dr. Kojo Boateng',
            'phone_number': '+233 24 555 1234',
            'email': 'kojo.boateng@apexenergy.gh',
            'accessibility_required': 'on',
            'executive_vehicle_required': 'on',
            'additional_stops_notes': 'Wheelchair ramp required, VIP chauffeur attire requested.',
        }
        response = self.client.post(reverse('portal_new_request'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        req = TransportationRequest.objects.filter(pickup_address='Ridge Hospital, Accra').first()
        self.assertIsNotNone(req)
        self.assertTrue(req.accessibility_required)
        self.assertTrue(req.executive_vehicle_required)
        self.assertEqual(req.additional_stops_notes, 'Wheelchair ramp required, VIP chauffeur attire requested.')
        self.assertEqual(req.customer, self.corporate_company)

    def test_provider_can_update_driver_status_quick_action(self):
        """Test provider can update driver status using the update_driver_status action."""
        provider_user = User.objects.create_user(
            username='provider_admin_test',
            email='dispatch@goldstar.gh',
            role=User.Role.PROVIDER_ADMIN,
            password='TestPassword123!'
        )
        driver = Driver.objects.create(
            provider=self.provider,
            full_name='Emmanuel Osei',
            phone_number='+233 24 123 4567',
            license_number='DL-GH-1234',
            status=Driver.Status.AVAILABLE
        )
        self.client.login(username='provider_admin_test', password='TestPassword123!')

        # Update to OFF_DUTY
        response = self.client.post(reverse('portal_provider_drivers'), {
            'action': 'update_driver_status',
            'driver_id': driver.id,
            'status': Driver.Status.OFF_DUTY
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        driver.refresh_from_db()
        self.assertEqual(driver.status, Driver.Status.OFF_DUTY)

        # Update to INACTIVE
        response = self.client.post(reverse('portal_provider_drivers'), {
            'action': 'update_driver_status',
            'driver_id': driver.id,
            'status': Driver.Status.INACTIVE
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        driver.refresh_from_db()
        self.assertEqual(driver.status, Driver.Status.INACTIVE)

    def test_provider_can_update_driver_status_via_edit_driver(self):
        """Test provider can update driver status and details simultaneously via edit_driver."""
        provider_user = User.objects.create_user(
            username='provider_admin_edit_test',
            email='dispatch@goldstar.gh',
            role=User.Role.PROVIDER_ADMIN,
            password='TestPassword123!'
        )
        driver = Driver.objects.create(
            provider=self.provider,
            full_name='Yaw Mensah',
            phone_number='+233 24 777 8888',
            license_number='DL-GH-7788',
            status=Driver.Status.AVAILABLE
        )
        self.client.login(username='provider_admin_edit_test', password='TestPassword123!')

        response = self.client.post(reverse('portal_provider_drivers'), {
            'action': 'edit_driver',
            'driver_id': driver.id,
            'full_name': 'Yaw Mensah Snr',
            'phone_number': '+233 24 777 9999',
            'license_number': 'DL-GH-7788',
            'languages_spoken': 'English, Twi',
            'status': Driver.Status.ON_TRIP
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        driver.refresh_from_db()
        self.assertEqual(driver.full_name, 'Yaw Mensah Snr')
        self.assertEqual(driver.phone_number, '+233 24 777 9999')
        self.assertEqual(driver.status, Driver.Status.ON_TRIP)



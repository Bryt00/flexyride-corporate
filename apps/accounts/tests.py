from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase
from accounts.models import User, CorporateCustomer, CompanyEmployee, ProviderCompany


class AccountsModelTests(TestCase):
    def test_create_user_with_role(self):
        user = User.objects.create_user(
            username='corporate_rep_1',
            email='rep@company.com',
            password='Password123!',
            role=User.Role.CUSTOMER
        )
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertEqual(str(user), "corporate_rep_1 (Corporate Customer)")

    def test_corporate_customer_and_employee_setup(self):
        company = CorporateCustomer.objects.create(
            company_name="Acme Tech Ghana",
            registration_number="REG-991823",
            contact_email="admin@acme.com.gh",
            contact_phone="+233240000001",
            status=CorporateCustomer.Status.APPROVED
        )
        user = User.objects.create_user(
            username='manager_acme',
            email='manager@acme.co.ug',
            password='Password123!',
            role=User.Role.CUSTOMER
        )
        employee = CompanyEmployee.objects.create(
            company=company,
            user=user,
            can_approve_requests=True,
            spending_limit=500000.00
        )
        self.assertTrue(employee.can_approve_requests)
        self.assertEqual(employee.spending_limit, 500000.00)
        self.assertEqual(str(employee), "manager_acme - Acme Tech Ghana")

    def test_provider_company_creation(self):
        provider = ProviderCompany.objects.create(
            company_name="Swift Executive Transport",
            registration_number="PRV-8821",
            contact_person="John Driver",
            phone="+233240000002",
            email="info@swifttransport.com.gh",
            status=ProviderCompany.Status.APPROVED
        )
        self.assertEqual(provider.status, ProviderCompany.Status.APPROVED)
        self.assertEqual(str(provider), "Swift Executive Transport [Approved]")

    def test_provider_subaccount_code_creation_with_bank_details(self):
        """Test creating an approved provider with bank details auto-generates Paystack subaccount code."""
        provider = ProviderCompany.objects.create(
            company_name="Royal Transit Ghana",
            registration_number="DVLA-GH-ROYAL-01",
            contact_person="Emmanuel Osei",
            phone="+233241112233",
            email="dispatch@royaltransit.gh",
            status=ProviderCompany.Status.APPROVED,
            payout_channel=ProviderCompany.PayoutChannel.BANK,
            settlement_bank="040100",
            settlement_bank_name="GCB Bank Limited",
            account_number="04010012345678",
            account_name="ROYAL TRANSIT GHANA LTD",
            percentage_charge=Decimal("4.50"),
        )
        self.assertTrue(provider.has_payout_details)
        self.assertTrue(bool(provider.paystack_subaccount_code))
        self.assertTrue(provider.paystack_subaccount_code.startswith("ACCT_"))
        self.assertIsNotNone(provider.paystack_subaccount_synced_at)

    @patch('payments.paystack.create_subaccount')
    def test_provider_subaccount_code_with_mocked_paystack_api(self, mock_create):
        """Test Paystack create_subaccount API response properly populates subaccount code and status."""
        mock_create.return_value = {
            'success': True,
            'subaccount_code': 'ACCT_live_subaccount_8899',
            'account_name': 'ELITE SHUTTLES GHANA',
            'settlement_bank_name': 'Ecobank Ghana Limited',
        }
        provider = ProviderCompany.objects.create(
            company_name="Elite Shuttles Ghana",
            registration_number="DVLA-GH-ELITE-02",
            contact_person="Nana Kwabena",
            phone="+233249998877",
            email="dispatch@eliteshuttles.gh",
            status=ProviderCompany.Status.APPROVED,
            payout_channel=ProviderCompany.PayoutChannel.BANK,
            settlement_bank="130100",
            account_number="13010098765432",
        )
        self.assertEqual(provider.paystack_subaccount_code, "ACCT_live_subaccount_8899")
        self.assertEqual(provider.account_name, "ELITE SHUTTLES GHANA")
        self.assertEqual(provider.settlement_bank_name, "Ecobank Ghana Limited")
        self.assertEqual(provider.paystack_subaccount_status, "Active on Paystack")
        self.assertIsNotNone(provider.paystack_subaccount_synced_at)

    def test_provider_pending_does_not_create_subaccount_until_approved(self):
        """Test a provider created with PENDING status does not create subaccount until approved."""
        provider = ProviderCompany.objects.create(
            company_name="Pending Logistics",
            registration_number="DVLA-GH-PENDING-03",
            contact_person="Kojo Mensah",
            phone="+233245554433",
            email="dispatch@pendinglogistics.gh",
            status=ProviderCompany.Status.PENDING,
            settlement_bank="040100",
            account_number="04010099887766",
        )
        self.assertIsNone(provider.paystack_subaccount_code)

        # Now approve the provider
        provider.status = ProviderCompany.Status.APPROVED
        provider.save()

        provider.refresh_from_db()
        self.assertTrue(bool(provider.paystack_subaccount_code))
        self.assertTrue(provider.paystack_subaccount_code.startswith("ACCT_"))

    def test_provider_momo_subaccount_code_creation(self):
        """Test creating a provider with Mobile Money channel generates subaccount code."""
        provider = ProviderCompany.objects.create(
            company_name="Tema MoMo Transporters",
            registration_number="DVLA-GH-MOMO-04",
            contact_person="Amina Adams",
            phone="+233244112233",
            email="dispatch@temamomo.gh",
            status=ProviderCompany.Status.APPROVED,
            payout_channel=ProviderCompany.PayoutChannel.MOBILE_MONEY,
            settlement_bank="MTN",
            settlement_bank_name="MTN Mobile Money",
            account_number="0244112233",
            account_name="TEMA MOMO TRANSPORTERS",
        )
        self.assertEqual(provider.payout_channel, ProviderCompany.PayoutChannel.MOBILE_MONEY)
        self.assertEqual(provider.settlement_bank, "MTN")
        self.assertEqual(provider.account_number, "0244112233")
        self.assertTrue(bool(provider.paystack_subaccount_code))
        self.assertTrue(provider.paystack_subaccount_code.startswith("ACCT_"))


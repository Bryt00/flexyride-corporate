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


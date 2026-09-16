import os
import sys
from pathlib import Path
import django

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / 'apps'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User, CorporateCustomer, CompanyEmployee, ProviderCompany

def seed_data():
    # 1. Create Broker
    broker_user, created = User.objects.get_or_create(
        username='broker_admin',
        defaults={
            'email': 'broker@flexyride.com',
            'role': User.Role.BROKER,
            'first_name': 'Flexy',
            'last_name': 'Broker'
        }
    )
    if created:
        broker_user.set_password('password123')
        broker_user.save()
        print("Created broker_admin (Password: password123)")

    # 2. Create Corporate Customer
    customer_user, created = User.objects.get_or_create(
        username='customer',
        defaults={
            'email': 'rep@mtn.com',
            'role': User.Role.CUSTOMER,
            'first_name': 'John',
            'last_name': 'Doe'
        }
    )
    if created:
        customer_user.set_password('password123')
        customer_user.save()
        print("Created customer (Password: password123)")

    mtn, created = CorporateCustomer.objects.get_or_create(
        company_name='MTN Ghana',
        defaults={
            'contact_email': 'rep@mtn.com.gh',
            'contact_phone': '+233240000000',
            'status': CorporateCustomer.Status.APPROVED,
            'preferred_currency': 'GHS'
        }
    )
    
    CompanyEmployee.objects.get_or_create(
        user=customer_user,
        company=mtn,
        defaults={'can_approve_requests': True}
    )
    print("Created MTN Ghana and linked customer")

    # 3. Create Provider & Provider Admin
    provider_admin, created = User.objects.get_or_create(
        username='provider_admin',
        defaults={
            'email': 'admin@safari.com',
            'role': User.Role.PROVIDER_ADMIN,
            'first_name': 'Safari',
            'last_name': 'Admin'
        }
    )
    if created:
        provider_admin.set_password('password123')
        provider_admin.save()
        print("Created provider_admin (Password: password123)")

    safari, created = ProviderCompany.objects.get_or_create(
        company_name='Gold Coast Express Logistics',
        defaults={
            'email': 'admin@safari.com',
            'contact_person': 'Safari Admin',
            'phone': '+233302000000',
            'status': ProviderCompany.Status.APPROVED,
            'service_area': 'Accra, Tema, Kumasi, Takoradi'
        }
    )
    print("Created Gold Coast Express Logistics and linked to provider_admin via email")

if __name__ == '__main__':
    seed_data()
    print("Seeding complete.")

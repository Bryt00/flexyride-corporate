import os
import django
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexyride_corporate.settings')
django.setup()

from accounts.models import User, CorporateCustomer, CompanyEmployee, ProviderCompany
from fleet.models import Vehicle, Driver
from bookings.models import TransportationRequest, VehicleAssignment, PassengerInfo
from quotations.models import ProviderQuoteRequest, ProviderQuote, CustomerQuote
from compliance.models import ComplianceDocument

def seed_full():
    print("Seeding full ecosystem for Ghana, West Africa...")
    
    # 1. Ensure Provider Company & Admin
    provider_admin, _ = User.objects.get_or_create(
        username='provider_admin',
        defaults={
            'email': 'admin@safari.com',
            'role': User.Role.PROVIDER_ADMIN,
            'first_name': 'Safari',
            'last_name': 'Admin'
        }
    )
    provider_admin.set_password('password123')
    provider_admin.save()

    safari, _ = ProviderCompany.objects.get_or_create(
        company_name='Safari Transport Ltd',
        defaults={
            'email': 'admin@safari.com',
            'contact_person': 'Safari Admin',
            'phone': '+233302000000',
            'status': ProviderCompany.Status.APPROVED,
            'service_area': 'Accra, Tema, Kumasi, Takoradi'
        }
    )
    safari.email = 'admin@safari.com'
    safari.phone = '+233302000000'
    safari.service_area = 'Accra, Tema, Kumasi, Takoradi'
    safari.address = 'Liberation Road, Airport City, Accra, Ghana'
    safari.save()

    # 2. Corporate Customer
    customer_user, _ = User.objects.get_or_create(
        username='customer',
        defaults={
            'email': 'rep@mtn.com.gh',
            'role': User.Role.CUSTOMER,
            'first_name': 'John',
            'last_name': 'Mensah'
        }
    )
    customer_user.set_password('password123')
    customer_user.save()

    CorporateCustomer.objects.filter(company_name__icontains='Uganda').update(
        company_name='MTN Ghana Corporate',
        preferred_currency='GHS',
        address='MTN House, Plot Osu Badu Street, Airport City, Accra',
        contact_email='rep@mtn.com.gh',
        contact_phone='+233240000000'
    )

    mtn = CorporateCustomer.objects.filter(company_name='MTN Ghana Corporate').first()
    if not mtn:
        mtn = CorporateCustomer.objects.create(
            company_name='MTN Ghana Corporate',
            contact_email='rep@mtn.com.gh',
            contact_phone='+233240000000',
            status=CorporateCustomer.Status.APPROVED,
            preferred_currency='GHS',
            credit_limit=Decimal('150000.00'),
            address='MTN House, Plot Osu Badu Street, Airport City, Accra'
        )
    else:
        mtn.preferred_currency = 'GHS'
        mtn.contact_email = 'rep@mtn.com.gh'
        mtn.contact_phone = '+233240000000'
        mtn.address = 'MTN House, Plot Osu Badu Street, Airport City, Accra'
        mtn.save()

    emp, _ = CompanyEmployee.objects.get_or_create(
        user=customer_user,
        defaults={'company': mtn, 'can_approve_requests': True}
    )
    emp.company = mtn
    emp.save()

    # 3. Broker Admin
    broker_user, _ = User.objects.get_or_create(
        username='broker_admin',
        defaults={
            'email': 'broker@flexyride.com',
            'role': User.Role.BROKER,
            'first_name': 'Flexy',
            'last_name': 'Broker'
        }
    )
    broker_user.set_password('password123')
    broker_user.is_staff = True
    broker_user.save()

    # System Admin / Executive Superuser
    sys_admin, _ = User.objects.get_or_create(
        username='system_admin',
        defaults={
            'email': 'admin@flexyride.com',
            'role': User.Role.SYSTEM_ADMIN,
            'first_name': 'System',
            'last_name': 'Administrator',
            'is_staff': True,
            'is_superuser': True,
        }
    )
    sys_admin.is_staff = True
    sys_admin.is_superuser = True
    sys_admin.set_password('password123')
    sys_admin.save()

    # 4. Vehicles for Provider (Ghana registration standards)
    v1, _ = Vehicle.objects.get_or_create(
        registration_number='GS 4821-24',
        defaults={
            'provider': safari,
            'make': 'Toyota',
            'model': 'Prado TX',
            'year': 2024,
            'color': 'Pearl White',
            'category': Vehicle.Category.SUV,
            'seating_capacity': 5,
            'wifi_available': True,
            'water_provided': True,
            'status': Vehicle.Status.AVAILABLE,
            'compliance_status': Vehicle.ComplianceStatus.COMPLIANT
        }
    )

    v2, _ = Vehicle.objects.get_or_create(
        registration_number='GW 1082-23',
        defaults={
            'provider': safari,
            'make': 'Mercedes-Benz',
            'model': 'E200 Avantgarde',
            'year': 2023,
            'color': 'Obsidian Black',
            'category': Vehicle.Category.EXECUTIVE,
            'seating_capacity': 4,
            'wifi_available': True,
            'water_provided': True,
            'status': Vehicle.Status.AVAILABLE,
            'compliance_status': Vehicle.ComplianceStatus.COMPLIANT
        }
    )

    v3, _ = Vehicle.objects.get_or_create(
        registration_number='GT 3140-23',
        defaults={
            'provider': safari,
            'make': 'Toyota',
            'model': 'Coaster Executive',
            'year': 2023,
            'color': 'Silver Metallic',
            'category': Vehicle.Category.COASTER_BUS,
            'seating_capacity': 28,
            'wifi_available': True,
            'water_provided': True,
            'status': Vehicle.Status.AVAILABLE,
            'compliance_status': Vehicle.ComplianceStatus.COMPLIANT
        }
    )

    v4, _ = Vehicle.objects.get_or_create(
        registration_number='GE 7780-22',
        defaults={
            'provider': safari,
            'make': 'Toyota',
            'model': 'HiAce Super Custom',
            'year': 2022,
            'color': 'Champagne Gold',
            'category': Vehicle.Category.VAN,
            'seating_capacity': 9,
            'wifi_available': True,
            'water_provided': True,
            'status': Vehicle.Status.AVAILABLE,
            'compliance_status': Vehicle.ComplianceStatus.COMPLIANT
        }
    )

    v5, _ = Vehicle.objects.get_or_create(
        registration_number='GN 1010-24',
        defaults={
            'provider': safari,
            'make': 'Toyota',
            'model': 'Land Cruiser V8 VIP',
            'year': 2024,
            'color': 'Midnight Black',
            'category': Vehicle.Category.LUXURY,
            'seating_capacity': 5,
            'wifi_available': True,
            'water_provided': True,
            'status': Vehicle.Status.ASSIGNED,
            'compliance_status': Vehicle.ComplianceStatus.COMPLIANT
        }
    )

    v6, _ = Vehicle.objects.get_or_create(
        registration_number='GS 6200-23',
        defaults={
            'provider': safari,
            'make': 'Toyota',
            'model': 'RAV4 Hybrid',
            'year': 2023,
            'color': 'Dark Grey',
            'category': Vehicle.Category.SUV,
            'seating_capacity': 4,
            'wifi_available': False,
            'water_provided': True,
            'status': Vehicle.Status.AVAILABLE,
            'compliance_status': Vehicle.ComplianceStatus.COMPLIANT
        }
    )

    # 5. Professional Drivers in Ghana
    d1, _ = Driver.objects.get_or_create(
        license_number='DL-88912-GH',
        defaults={
            'provider': safari,
            'full_name': 'Kofi Mensah',
            'phone_number': '+233 24 412 3456',
            'languages_spoken': 'English, Twi, Ga',
            'status': Driver.Status.AVAILABLE,
            'compliance_status': Driver.ComplianceStatus.COMPLIANT,
            'rating': Decimal('4.92')
        }
    )

    d2, _ = Driver.objects.get_or_create(
        license_number='DL-55421-GH',
        defaults={
            'provider': safari,
            'full_name': 'Abena Osei',
            'phone_number': '+233 20 891 2345',
            'languages_spoken': 'English, Twi, Fante',
            'status': Driver.Status.AVAILABLE,
            'compliance_status': Driver.ComplianceStatus.COMPLIANT,
            'rating': Decimal('4.88')
        }
    )

    d3, _ = Driver.objects.get_or_create(
        license_number='DL-77319-GH',
        defaults={
            'provider': safari,
            'full_name': 'Kwame Asante',
            'phone_number': '+233 24 991 8821',
            'languages_spoken': 'English, Twi, Hausa',
            'status': Driver.Status.ON_TRIP,
            'compliance_status': Driver.ComplianceStatus.COMPLIANT,
            'rating': Decimal('4.95')
        }
    )

    d4, _ = Driver.objects.get_or_create(
        license_number='DL-99210-GH',
        defaults={
            'provider': safari,
            'full_name': 'Emmanuel Addo',
            'phone_number': '+233 50 334 1122',
            'languages_spoken': 'English, Ga, Twi',
            'status': Driver.Status.AVAILABLE,
            'compliance_status': Driver.ComplianceStatus.COMPLIANT,
            'rating': Decimal('4.79')
        }
    )

    d5, _ = Driver.objects.get_or_create(
        license_number='DL-33108-GH',
        defaults={
            'provider': safari,
            'full_name': 'Yaw Boateng',
            'phone_number': '+233 24 771 9090',
            'languages_spoken': 'English, Twi, Ewe',
            'status': Driver.Status.OFF_DUTY,
            'compliance_status': Driver.ComplianceStatus.COMPLIANT,
            'rating': Decimal('4.85')
        }
    )

    # 6. Compliance Documents (DVLA, GRA, Insurance)
    ComplianceDocument.objects.get_or_create(
        document_number='DVLA-LIC-2026-GH',
        defaults={
            'provider': safari,
            'document_type': ComplianceDocument.DocumentType.BUSINESS_LICENSE,
            'target_type': ComplianceDocument.TargetType.PROVIDER,
            'issue_date': timezone.now().date() - timedelta(days=120),
            'expiry_date': timezone.now().date() + timedelta(days=365),
            'status': ComplianceDocument.Status.APPROVED
        }
    )

    ComplianceDocument.objects.get_or_create(
        document_number='POL-SIC-8849-GH',
        defaults={
            'provider': safari,
            'document_type': ComplianceDocument.DocumentType.INSURANCE,
            'target_type': ComplianceDocument.TargetType.PROVIDER,
            'issue_date': timezone.now().date() - timedelta(days=60),
            'expiry_date': timezone.now().date() + timedelta(days=300),
            'status': ComplianceDocument.Status.APPROVED
        }
    )

    ComplianceDocument.objects.get_or_create(
        document_number='DVLA-INSP-9912',
        defaults={
            'provider': safari,
            'document_type': ComplianceDocument.DocumentType.ROADWORTHINESS,
            'target_type': ComplianceDocument.TargetType.PROVIDER,
            'issue_date': timezone.now().date() - timedelta(days=30),
            'expiry_date': timezone.now().date() + timedelta(days=150),
            'status': ComplianceDocument.Status.APPROVED
        }
    )

    ComplianceDocument.objects.get_or_create(
        document_number='GRA-TCC-2026-GH',
        defaults={
            'provider': safari,
            'document_type': ComplianceDocument.DocumentType.TAX_CERTIFICATE,
            'target_type': ComplianceDocument.TargetType.PROVIDER,
            'issue_date': timezone.now().date() - timedelta(days=90),
            'expiry_date': timezone.now().date() + timedelta(days=275),
            'status': ComplianceDocument.Status.APPROVED
        }
    )

    # 7. Transportation Requests & RFQs (Accra & Greater Accra routes)
    now = timezone.now()

    # RFQ 1: Pending Quote (Airport Meet & Greet)
    req1, _ = TransportationRequest.objects.get_or_create(
        request_number='FRC-2026-0041',
        defaults={
            'customer': mtn,
            'requester': customer_user,
            'journey_type': TransportationRequest.JourneyType.AIRPORT_MEET_GREET,
            'pickup_address': 'MTN House, Independence Avenue, Ridge, Accra',
            'destination_address': 'Kotoka International Airport (ACC) · Terminal 3',
            'departure_datetime': now + timedelta(days=1, hours=4),
            'requested_vehicle_category': 'SUV',
            'vehicles_requested_count': 1,
            'passenger_count': 2,
            'estimated_distance_km': Decimal('8.5'),
            'priority_level': TransportationRequest.PriorityLevel.URGENT,
            'executive_vehicle_required': True,
            'luggage_requirements': '3 Large Samsonite Suitcases',
            'booking_status': TransportationRequest.BookingStatus.AWAITING_INTERNAL_APPROVAL,
            'internal_approval_status': TransportationRequest.InternalApprovalStatus.PENDING_APPROVAL,
            'assigned_broker': broker_user
        }
    )
    req1.internal_approval_status = TransportationRequest.InternalApprovalStatus.PENDING_APPROVAL
    req1.booking_status = TransportationRequest.BookingStatus.AWAITING_INTERNAL_APPROVAL
    req1.save()

    PassengerInfo.objects.get_or_create(
        request=req1,
        full_name='Selorm Adadevoh',
        defaults={'phone_number': '+233 24 400 0001', 'email': 'selorm@mtn.com.gh', 'is_primary': True}
    )
    pqr1, _ = ProviderQuoteRequest.objects.get_or_create(
        request=req1,
        provider=safari,
        defaults={'status': ProviderQuoteRequest.Status.SENT}
    )

    # RFQ 2: Already Quoted (Executive Saloon Event)
    req2, _ = TransportationRequest.objects.get_or_create(
        request_number='FRC-2026-0048',
        defaults={
            'customer': mtn,
            'requester': customer_user,
            'journey_type': TransportationRequest.JourneyType.EVENT,
            'pickup_address': 'Kempinski Hotel Gold Coast City, Gamel Abdul Nasser Ave, Accra',
            'destination_address': 'Labadi Beach Hotel & Conference Centre, Accra',
            'departure_datetime': now + timedelta(days=3, hours=2),
            'requested_vehicle_category': 'EXECUTIVE',
            'vehicles_requested_count': 1,
            'passenger_count': 3,
            'estimated_distance_km': Decimal('10.2'),
            'priority_level': TransportationRequest.PriorityLevel.STANDARD,
            'executive_vehicle_required': True,
            'booking_status': TransportationRequest.BookingStatus.QUOTE_AVAILABLE,
            'assigned_broker': broker_user
        }
    )
    pqr2, _ = ProviderQuoteRequest.objects.get_or_create(
        request=req2,
        provider=safari,
        defaults={'status': ProviderQuoteRequest.Status.RESPONDED}
    )
    pq2, _ = ProviderQuote.objects.get_or_create(
        quote_request=pqr2,
        provider=safari,
        defaults={
            'offered_cost': Decimal('450.00'),
            'proposed_vehicle': v2,
            'status': ProviderQuote.Status.SUBMITTED,
            'notes': 'Mercedes E200 available with dedicated VIP protocol chauffeur and bottled mineral water provided.'
        }
    )

    # Customer Quotes
    cq1, _ = CustomerQuote.objects.get_or_create(
        request=req2,
        defaults={
            'selected_provider_quote': pq2,
            'provider_cost': Decimal('450.00'),
            'margin_amount': Decimal('150.00'),
            'final_customer_price': Decimal('600.00'),
            'status': CustomerQuote.Status.SENT,
            'created_by': broker_user,
            'sent_at': now - timedelta(hours=3)
        }
    )
    cq2, _ = CustomerQuote.objects.get_or_create(
        request=req1,
        defaults={
            'provider_cost': Decimal('320.00'),
            'margin_amount': Decimal('80.00'),
            'final_customer_price': Decimal('400.00'),
            'status': CustomerQuote.Status.DRAFT,
            'created_by': broker_user
        }
    )

    # RFQ 3: Awarded & Live In-Transit Trip
    req3, _ = TransportationRequest.objects.get_or_create(
        request_number='FRC-2026-0033',
        defaults={
            'customer': mtn,
            'requester': customer_user,
            'journey_type': TransportationRequest.JourneyType.ONE_WAY,
            'pickup_address': 'East Legon, Boundary Road, Accra',
            'destination_address': 'Mövenpick Ambassador Hotel, Ridge, Accra',
            'departure_datetime': now - timedelta(minutes=45),
            'requested_vehicle_category': 'LUXURY',
            'vehicles_requested_count': 1,
            'passenger_count': 1,
            'estimated_distance_km': Decimal('11.5'),
            'priority_level': TransportationRequest.PriorityLevel.STANDARD,
            'booking_status': TransportationRequest.BookingStatus.TRIP_IN_PROGRESS,
            'assigned_broker': broker_user
        }
    )
    req3.booking_status = TransportationRequest.BookingStatus.TRIP_IN_PROGRESS
    req3.save()

    PassengerInfo.objects.get_or_create(
        request=req3,
        full_name='Dr. Kwame Baah',
        defaults={'phone_number': '+233 24 192 0180', 'email': 'kbaah@mtn.com.gh', 'is_primary': True}
    )
    VehicleAssignment.objects.get_or_create(
        request=req3,
        vehicle=v5,
        driver=d3,
        defaults={'status': VehicleAssignment.Status.TRIP_IN_PROGRESS}
    )

    # RFQ 4: Awarded Scheduled Trip for Tomorrow
    req4, _ = TransportationRequest.objects.get_or_create(
        request_number='FRC-2026-0052',
        defaults={
            'customer': mtn,
            'requester': customer_user,
            'journey_type': TransportationRequest.JourneyType.FULL_DAY,
            'pickup_address': 'MTN House, Ridge, Accra',
            'destination_address': 'Tema Free Zones Enclave & Port Logistics Hub',
            'departure_datetime': now + timedelta(days=1, hours=1),
            'requested_vehicle_category': 'COASTER_BUS',
            'vehicles_requested_count': 1,
            'passenger_count': 22,
            'estimated_distance_km': Decimal('32.0'),
            'priority_level': TransportationRequest.PriorityLevel.STANDARD,
            'booking_status': TransportationRequest.BookingStatus.CONFIRMED,
            'assigned_broker': broker_user
        }
    )
    req4.booking_status = TransportationRequest.BookingStatus.CONFIRMED
    req4.save()

    VehicleAssignment.objects.get_or_create(
        request=req4,
        vehicle=v3,
        driver=d1,
        defaults={'status': VehicleAssignment.Status.ASSIGNED}
    )

    # 8. Corporate Invoices (Accounts Receivable)
    from payments.models import PaymentTransaction, Invoice
    inv1, _ = Invoice.objects.get_or_create(
        invoice_number='INV-2026-0081',
        defaults={
            'customer': mtn,
            'billing_period_start': (now - timedelta(days=30)).date(),
            'billing_period_end': now.date(),
            'subtotal': Decimal('12500.00'),
            'tax_amount': Decimal('2187.50'),
            'total': Decimal('14687.50'),
            'currency': 'GHS',
            'status': Invoice.Status.SENT,
            'due_date': (now + timedelta(days=15)).date(),
            'notes': 'Corporate Executive Shuttle Services - August 2026'
        }
    )
    inv2, _ = Invoice.objects.get_or_create(
        invoice_number='INV-2026-0072',
        defaults={
            'customer': mtn,
            'billing_period_start': (now - timedelta(days=60)).date(),
            'billing_period_end': (now - timedelta(days=30)).date(),
            'subtotal': Decimal('8000.00'),
            'tax_amount': Decimal('1400.00'),
            'total': Decimal('9400.00'),
            'currency': 'GHS',
            'status': Invoice.Status.OVERDUE,
            'due_date': (now - timedelta(days=5)).date(),
            'notes': 'Airport VIP Protocol Fleet - July 2026 (Payment overdue)'
        }
    )

    # 9. Compliance Flags (Expiring Soon & Expired)
    cd1, _ = ComplianceDocument.objects.get_or_create(
        document_number='POL-SIC-V1-2026',
        defaults={
            'provider': safari,
            'vehicle': v1,
            'document_type': ComplianceDocument.DocumentType.INSURANCE,
            'target_type': ComplianceDocument.TargetType.VEHICLE,
            'issue_date': (now - timedelta(days=350)).date(),
            'expiry_date': (now + timedelta(days=15)).date(),
            'status': ComplianceDocument.Status.EXPIRING_SOON
        }
    )
    cd1.status = ComplianceDocument.Status.EXPIRING_SOON
    cd1.expiry_date = (now + timedelta(days=15)).date()
    cd1.save()

    cd2, _ = ComplianceDocument.objects.get_or_create(
        document_number='DL-GH-88210',
        defaults={
            'provider': safari,
            'driver': d1,
            'document_type': ComplianceDocument.DocumentType.DRIVERS_LICENSE,
            'target_type': ComplianceDocument.TargetType.DRIVER,
            'issue_date': (now - timedelta(days=730)).date(),
            'expiry_date': (now - timedelta(days=10)).date(),
            'status': ComplianceDocument.Status.EXPIRED
        }
    )
    cd2.status = ComplianceDocument.Status.EXPIRED
    cd2.expiry_date = (now - timedelta(days=10)).date()
    cd2.save()

    # 10. Currency & Regional Migration for Existing Records
    PaymentTransaction.objects.filter(currency='UGX').update(currency='GHS')
    Invoice.objects.filter(currency='UGX').update(currency='GHS')
    CorporateCustomer.objects.filter(preferred_currency='UGX').update(preferred_currency='GHS')

    # Update any old trips with Kampala/Entebbe addresses to Accra/Kotoka
    TransportationRequest.objects.filter(pickup_address__icontains='Kampala').update(
        pickup_address='Kempinski Hotel Gold Coast City, Accra'
    )
    TransportationRequest.objects.filter(destination_address__icontains='Entebbe').update(
        destination_address='Kotoka International Airport (ACC) · Terminal 3'
    )
    TransportationRequest.objects.filter(destination_address__icontains='Kampala').update(
        destination_address='Liberation Road, Airport City, Accra'
    )
    TransportationRequest.objects.filter(destination_address__icontains='Jinja').update(
        destination_address='Tema Free Zones Enclave & Port Logistics Hub'
    )

    print("Full ecosystem seeding and Ghana localization migration successful!")

if __name__ == '__main__':
    seed_full()

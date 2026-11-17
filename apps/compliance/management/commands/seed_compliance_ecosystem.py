"""
Management command to seed compliance ecosystem data, including:
1. Section 13 Test Case: Excoba Car Rental (Suspended, Expired Operator Licence, Suspended Vehicles, Audit Trail).
2. Compliant Reference: Gold Coast Express Logistics (Verified Operator Licence, Verified Fleet, Active Paystack).
3. Expiring Soon Provider: Safari Fleet Services (Operator Licence expiring in 12 days, testing 14-day warning threshold).
"""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils import timezone
from django.contrib.auth import get_user_model

from accounts.models import ProviderCompany
from fleet.models import Vehicle
from compliance.models import ComplianceDocument, ComplianceAuditLog

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds Paystack compliance demonstration data, including Excoba Car Rental suspension test case.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("--- SEEDING COMPLIANCE ECOSYSTEM ---"))
        today = timezone.now().date()
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.filter(role='SYSTEM_ADMIN').first()

        # =========================================================================
        # 1. EXCOBA CAR RENTAL (Section 13 Suspension Test Case)
        # =========================================================================
        excoba, created = ProviderCompany.objects.get_or_create(
            company_name='Excoba Car Rental',
            defaults={
                'registration_number': 'CS-89210-2021',
                'contact_person': 'Excoba Daniels',
                'phone': '+233 24 555 0199',
                'email': 'compliance@excobacarrental.gh',
                'address': 'Plot 42, Spintex Road, Commercial District, Accra, Ghana',
                'status': ProviderCompany.Status.SUSPENDED,
                'overall_rating': 4.20,
                'service_area': 'Greater Accra, Tema, Eastern Region',
                'specializations': 'Executive sedans, Airport pickups',
                'settlement_bank': '057',
                'settlement_bank_name': 'Ecobank Ghana',
                'account_number': '1441002938471',
                'account_name': 'Excoba Car Rental Ltd',
                'paystack_subaccount_code': 'ACCT_excoba_test_01',
                'paystack_subaccount_status': 'active',
                'percentage_charge': 15.00,
            }
        )
        if not created:
            excoba.status = ProviderCompany.Status.SUSPENDED
            excoba.save()

        # Excoba Expired Operator Licence
        op_doc_excoba, _ = ComplianceDocument.objects.get_or_create(
            provider=excoba,
            document_type=ComplianceDocument.DocumentType.OPERATOR_LICENSE,
            defaults={
                'target_type': ComplianceDocument.TargetType.PROVIDER,
                'document_number': 'DVLA-OP-2023-EXCOBA',
                'issuing_authority': 'Ministry of Transport / DVLA Ghana',
                'issue_date': today - timedelta(days=400),
                'expiry_date': today - timedelta(days=35), # Expired 35 days ago
                'status': ComplianceDocument.Status.EXPIRED,
                'notes': 'Licence expired without timely renewal submission.',
                'verified_by': admin_user,
                'verified_at': timezone.now() - timedelta(days=400),
            }
        )
        if not op_doc_excoba.document_file:
            op_doc_excoba.document_file.save(
                'excoba_operator_license_expired.pdf',
                ContentFile(b"%PDF-1.4 [Sample Expired DVLA Commercial Vehicle Operator Licence for Excoba Car Rental]"),
                save=True
            )

        # Excoba Vehicles (must be suspended)
        v1, _ = Vehicle.objects.get_or_create(
            provider=excoba,
            registration_number='GW-4820-22',
            defaults={
                'make': 'Toyota',
                'model': 'Land Cruiser Prado',
                'year': 2022,
                'color': 'Black',
                'category': 'EXECUTIVE',
                'seating_capacity': 7,
                'luggage_capacity': '4 large bags',
                'wifi_available': True,
                'water_provided': True,
                'status': Vehicle.Status.AVAILABLE,
                'compliance_status': Vehicle.ComplianceStatus.SUSPENDED,
            }
        )
        v1.compliance_status = Vehicle.ComplianceStatus.SUSPENDED
        v1.save()

        # Documents for v1
        doc_v1_reg, _ = ComplianceDocument.objects.get_or_create(
            provider=excoba,
            vehicle=v1,
            document_type=ComplianceDocument.DocumentType.VEHICLE_REGISTRATION,
            defaults={
                'target_type': ComplianceDocument.TargetType.VEHICLE,
                'document_number': 'DVLA-VR-2022-4820',
                'issuing_authority': 'DVLA Ghana',
                'issue_date': today - timedelta(days=500),
                'expiry_date': None,
                'status': ComplianceDocument.Status.VERIFIED,
                'verified_by': admin_user,
                'verified_at': timezone.now() - timedelta(days=400),
            }
        )
        if not doc_v1_reg.document_file:
            doc_v1_reg.document_file.save('v1_reg.pdf', ContentFile(b"Sample DVLA Vehicle Registration GW-4820-22"), save=True)

        doc_v1_rw, _ = ComplianceDocument.objects.get_or_create(
            provider=excoba,
            vehicle=v1,
            document_type=ComplianceDocument.DocumentType.ROADWORTHINESS,
            defaults={
                'target_type': ComplianceDocument.TargetType.VEHICLE,
                'document_number': 'DVLA-RW-2023-9912',
                'issuing_authority': 'DVLA Vehicle Testing Center',
                'issue_date': today - timedelta(days=380),
                'expiry_date': today - timedelta(days=15), # Expired Roadworthiness
                'status': ComplianceDocument.Status.EXPIRED,
                'verified_by': admin_user,
                'verified_at': timezone.now() - timedelta(days=380),
            }
        )
        if not doc_v1_rw.document_file:
            doc_v1_rw.document_file.save('v1_rw.pdf', ContentFile(b"Sample DVLA Roadworthiness GW-4820-22"), save=True)

        v2, _ = Vehicle.objects.get_or_create(
            provider=excoba,
            registration_number='GE-7711-23',
            defaults={
                'make': 'Mercedes-Benz',
                'model': 'E-Class',
                'year': 2023,
                'color': 'Silver',
                'category': 'PREMIUM_SEDAN',
                'seating_capacity': 4,
                'luggage_capacity': '2 large bags',
                'wifi_available': True,
                'water_provided': True,
                'status': Vehicle.Status.AVAILABLE,
                'compliance_status': Vehicle.ComplianceStatus.SUSPENDED,
            }
        )
        v2.compliance_status = Vehicle.ComplianceStatus.SUSPENDED
        v2.save()

        # Audit log entry for Excoba suspension (Section 13 requirement)
        ComplianceAuditLog.objects.get_or_create(
            provider=excoba,
            action=ComplianceAuditLog.Action.PROVIDER_SUSPENSION,
            defaults={
                'actor': admin_user,
                'previous_status': 'APPROVED',
                'new_status': ProviderCompany.Status.SUSPENDED,
                'notes': (
                    "Provider: Excoba Car Rental | Action: Suspend from new bookings | "
                    "Reason: Operating licence not renewed | "
                    "Reactivation condition: Valid renewed licence uploaded, reviewed and approved, "
                    "with all other mandatory compliance requirements satisfied."
                ),
                'ip_address': '127.0.0.1',
            }
        )
        self.stdout.write(self.style.SUCCESS("[OK] Seeded Section 13 Test Case: Excoba Car Rental (SUSPENDED)"))

        # =========================================================================
        # 2. GOLD COAST EXPRESS LOGISTICS (Verified Reference Provider)
        # =========================================================================
        gc = ProviderCompany.objects.filter(company_name='Gold Coast Express Logistics').first()
        if gc:
            gc.status = ProviderCompany.Status.APPROVED
            gc.settlement_bank = '057'
            gc.settlement_bank_name = 'Ecobank Ghana'
            gc.account_number = '1441001234567'
            gc.account_name = 'Gold Coast Express Logistics Ltd'
            gc.paystack_subaccount_code = 'ACCT_gc_express_01'
            gc.paystack_subaccount_status = 'active'
            gc.percentage_charge = 15.00
            gc.save()

            op_gc, _ = ComplianceDocument.objects.get_or_create(
                provider=gc,
                document_type=ComplianceDocument.DocumentType.OPERATOR_LICENSE,
                defaults={
                    'target_type': ComplianceDocument.TargetType.PROVIDER,
                    'document_number': 'DVLA-OP-2024-GC01',
                    'issuing_authority': 'Ministry of Transport / DVLA Ghana',
                    'issue_date': today - timedelta(days=90),
                    'expiry_date': today + timedelta(days=275), # Valid for 275 days
                    'status': ComplianceDocument.Status.VERIFIED,
                    'verified_by': admin_user,
                    'verified_at': timezone.now() - timedelta(days=85),
                    'notes': 'Verified clean commercial operator licence.',
                }
            )
            if not op_gc.document_file:
                op_gc.document_file.save('gc_operator_licence.pdf', ContentFile(b"Sample Verified DVLA Licence GC"), save=True)

            # Update existing vehicle
            for veh in gc.vehicles.all():
                veh.compliance_status = Vehicle.ComplianceStatus.VERIFIED
                veh.save()
                doc_vr, _ = ComplianceDocument.objects.get_or_create(
                    provider=gc,
                    vehicle=veh,
                    document_type=ComplianceDocument.DocumentType.VEHICLE_REGISTRATION,
                    defaults={
                        'target_type': ComplianceDocument.TargetType.VEHICLE,
                        'document_number': f'DVLA-VR-{veh.registration_number}',
                        'issuing_authority': 'DVLA Ghana',
                        'issue_date': today - timedelta(days=180),
                        'expiry_date': None,
                        'status': ComplianceDocument.Status.VERIFIED,
                        'verified_by': admin_user,
                        'verified_at': timezone.now() - timedelta(days=175),
                    }
                )
                if not doc_vr.document_file:
                    doc_vr.document_file.save('gc_vr.pdf', ContentFile(b"Sample DVLA VR"), save=True)

                doc_rw, _ = ComplianceDocument.objects.get_or_create(
                    provider=gc,
                    vehicle=veh,
                    document_type=ComplianceDocument.DocumentType.ROADWORTHINESS,
                    defaults={
                        'target_type': ComplianceDocument.TargetType.VEHICLE,
                        'document_number': f'DVLA-RW-{veh.registration_number}',
                        'issuing_authority': 'DVLA Vehicle Testing Center',
                        'issue_date': today - timedelta(days=120),
                        'expiry_date': today + timedelta(days=245),
                        'status': ComplianceDocument.Status.VERIFIED,
                        'verified_by': admin_user,
                        'verified_at': timezone.now() - timedelta(days=115),
                    }
                )
                if not doc_rw.document_file:
                    doc_rw.document_file.save('gc_rw.pdf', ContentFile(b"Sample DVLA RW"), save=True)

            self.stdout.write(self.style.SUCCESS("[OK] Verified Reference Provider: Gold Coast Express Logistics (VERIFIED)"))

        # =========================================================================
        # 3. SAFARI FLEET SERVICES (Expiring Soon Test Case: 12 days to expiry)
        # =========================================================================
        safari, _ = ProviderCompany.objects.get_or_create(
            company_name='Safari Corporate Mobility',
            defaults={
                'registration_number': 'CS-44109-2022',
                'contact_person': 'Kwame Asante',
                'phone': '+233 20 882 1092',
                'email': 'fleet@safaricorporate.gh',
                'address': 'Airport Residential Area, Accra, Ghana',
                'status': ProviderCompany.Status.APPROVED,
                'overall_rating': 4.80,
                'service_area': 'Greater Accra, Kumasi Corridor',
                'specializations': 'Executive Vans & VIP Shuttles',
                'settlement_bank': '030',
                'settlement_bank_name': 'Standard Chartered Ghana',
                'account_number': '0100192837401',
                'account_name': 'Safari Corporate Mobility Services Ltd',
                'paystack_subaccount_code': 'ACCT_safari_test_01',
                'paystack_subaccount_status': 'active',
                'percentage_charge': 15.00,
            }
        )

        op_safari, _ = ComplianceDocument.objects.get_or_create(
            provider=safari,
            document_type=ComplianceDocument.DocumentType.OPERATOR_LICENSE,
            defaults={
                'target_type': ComplianceDocument.TargetType.PROVIDER,
                'document_number': 'DVLA-OP-2023-SAFARI',
                'issuing_authority': 'Ministry of Transport / DVLA Ghana',
                'issue_date': today - timedelta(days=353),
                'expiry_date': today + timedelta(days=12), # Expiring in 12 days!
                'status': ComplianceDocument.Status.EXPIRING_SOON,
                'verified_by': admin_user,
                'verified_at': timezone.now() - timedelta(days=350),
                'notes': 'Renewal notice dispatched (14-day window).',
            }
        )
        if not op_safari.document_file:
            op_safari.document_file.save('safari_op.pdf', ContentFile(b"Sample Safari Operator Licence"), save=True)

        v_safari, _ = Vehicle.objects.get_or_create(
            provider=safari,
            registration_number='GN-3390-21',
            defaults={
                'make': 'Toyota',
                'model': 'HiAce VIP Commuter',
                'year': 2021,
                'color': 'White',
                'category': 'VIP_COACH',
                'seating_capacity': 14,
                'luggage_capacity': '10 medium bags',
                'wifi_available': True,
                'water_provided': True,
                'status': Vehicle.Status.AVAILABLE,
                'compliance_status': Vehicle.ComplianceStatus.VERIFIED,
            }
        )
        doc_v_safari_reg, _ = ComplianceDocument.objects.get_or_create(
            provider=safari,
            vehicle=v_safari,
            document_type=ComplianceDocument.DocumentType.VEHICLE_REGISTRATION,
            defaults={
                'target_type': ComplianceDocument.TargetType.VEHICLE,
                'document_number': 'DVLA-VR-2021-3390',
                'issuing_authority': 'DVLA Ghana',
                'issue_date': today - timedelta(days=400),
                'expiry_date': None,
                'status': ComplianceDocument.Status.VERIFIED,
                'verified_by': admin_user,
                'verified_at': timezone.now() - timedelta(days=390),
            }
        )
        if not doc_v_safari_reg.document_file:
            doc_v_safari_reg.document_file.save('safari_v_reg.pdf', ContentFile(b"Sample VR"), save=True)

        doc_v_safari_rw, _ = ComplianceDocument.objects.get_or_create(
            provider=safari,
            vehicle=v_safari,
            document_type=ComplianceDocument.DocumentType.ROADWORTHINESS,
            defaults={
                'target_type': ComplianceDocument.TargetType.VEHICLE,
                'document_number': 'DVLA-RW-2023-3390',
                'issuing_authority': 'DVLA Vehicle Testing Center',
                'issue_date': today - timedelta(days=350),
                'expiry_date': today + timedelta(days=15), # Expiring in 15 days
                'status': ComplianceDocument.Status.EXPIRING_SOON,
                'verified_by': admin_user,
                'verified_at': timezone.now() - timedelta(days=340),
            }
        )
        if not doc_v_safari_rw.document_file:
            doc_v_safari_rw.document_file.save('safari_v_rw.pdf', ContentFile(b"Sample RW"), save=True)

        self.stdout.write(self.style.SUCCESS("[OK] Seeded Expiring Soon Provider: Safari Corporate Mobility (EXPIRING_SOON)"))
        self.stdout.write(self.style.SUCCESS("All compliance ecosystem test cases seeded successfully!"))


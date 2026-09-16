"""Business services and action dispatchers for portal operations.
Encapsulates mutations, status workflows, and transactions.
"""
import random
from decimal import Decimal
from django.db import transaction
from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from django.contrib.auth import update_session_auth_hash

from accounts.models import User, ProviderCompany
from bookings.models import TransportationRequest, VehicleAssignment
from fleet.models import Vehicle, Driver
from quotations.models import ProviderQuoteRequest, ProviderQuote, CustomerQuote, CommissionTier
from notifications.email_service import send_quote_ready_email
from notifications.models import Notification
from notifications.webpush import dispatch_notification
from compliance.models import ComplianceDocument


def handle_broker_post(request):
    """Processes mutation actions originating from broker workspaces."""
    action = request.POST.get('action')
    redirect_target = request.META.get('HTTP_REFERER') or 'portal_broker_overview'

    if action == 'broadcast_rfq':
        request_id = request.POST.get('request_id')
        req = TransportationRequest.objects.filter(id=request_id).first()
        if req:
            target_providers = ProviderCompany.objects.filter(status=ProviderCompany.Status.APPROVED)
            if not target_providers.exists():
                target_providers = ProviderCompany.objects.all()
            count = 0
            for provider in target_providers:
                pqr, created = ProviderQuoteRequest.objects.get_or_create(
                    request=req,
                    provider=provider,
                    defaults={'status': 'SENT'}
                )
                if created:
                    count += 1
            req.booking_status = 'BEING_ARRANGED'
            req.save(update_fields=['booking_status'])
            messages.success(request, f"Broadcasted RFQ tender for {req.request_number} to {count} transport providers.")
        else:
            messages.error(request, "Transportation request not found.")

    elif action == 'create_customer_quote':
        request_id = request.POST.get('request_id')
        provider_quote_id = request.POST.get('provider_quote_id')
        req = TransportationRequest.objects.filter(id=request_id).first()
        pq = ProviderQuote.objects.filter(id=provider_quote_id).first() if provider_quote_id else None

        if req:
            tier = CommissionTier.get_tier_for_request(req)
            margin_pct_input = request.POST.get('margin_pct')
            margin_pct = Decimal(margin_pct_input) if margin_pct_input else tier.margin_percentage

            provider_cost = pq.offered_cost if pq else Decimal(request.POST.get('provider_cost', '420'))
            margin_calc = provider_cost * (margin_pct / Decimal('100'))
            margin_amount = max(margin_calc, tier.min_margin_amount)
            final_price = provider_cost + margin_amount

            cq, _ = CustomerQuote.objects.update_or_create(
                request=req,
                defaults={
                    'selected_provider_quote': pq,
                    'provider_cost': provider_cost,
                    'margin_amount': margin_amount,
                    'final_customer_price': final_price,
                    'status': CustomerQuote.Status.SENT,
                    'created_by': request.user if request.user.is_authenticated else None,
                }
            )
            if pq:
                pq.status = ProviderQuote.Status.ACCEPTED_BY_BROKER
                pq.save(update_fields=['status'])

            req.booking_status = 'QUOTE_AVAILABLE'
            req.save(update_fields=['booking_status'])

            # Send automated quote notification email to corporate client
            send_quote_ready_email(cq, req)

            messages.success(request, f"Customer quote dispatched for {req.request_number} at GHS {final_price:,.2f} ({margin_pct}% margin applied). Client notified via email.")

    elif action == 'assign_dispatch':
        request_id = request.POST.get('request_id')
        vehicle_id = request.POST.get('vehicle_id')
        driver_id = request.POST.get('driver_id')
        req = TransportationRequest.objects.filter(id=request_id).first()
        vehicle = Vehicle.objects.filter(id=vehicle_id).first() if vehicle_id else None
        driver = Driver.objects.filter(id=driver_id).first() if driver_id else None

        # Automated Compliance Lockout Guard (US-92, US-110)
        if vehicle and not vehicle.is_compliant():
            messages.error(
                request,
                f"🚨 COMPLIANCE LOCKOUT: Cannot dispatch {vehicle.make} {vehicle.model} ({vehicle.registration_number}) — Roadworthiness or insurance has expired!"
            )
            return redirect(redirect_target)
        if driver and not driver.is_compliant():
            messages.error(
                request,
                f"🚨 COMPLIANCE LOCKOUT: Cannot dispatch {driver.full_name} — Driver's license or background vetting certification has expired!"
            )
            return redirect(redirect_target)

        if req and (vehicle or driver):
            VehicleAssignment.objects.update_or_create(
                request=req,
                defaults={
                    'vehicle': vehicle,
                    'driver': driver,
                    'status': 'ASSIGNED',
                    'assigned_by': request.user if request.user.is_authenticated else None,
                }
            )
            req.booking_status = 'ASSIGNED'
            req.save(update_fields=['booking_status'])

            if req.requester:
                dispatch_notification(
                    user=req.requester,
                    request_obj=req,
                    title="Fleet Unit Assigned",
                    message=f"Chauffeur {driver.full_name if driver else ''} assigned in {vehicle.make if vehicle else ''} ({vehicle.registration_number if vehicle else ''})",
                    notification_type=Notification.NotificationType.DRIVER_ASSIGNED,
                    url=f"/portal/bookings/{req.request_number}/confirmed/"
                )

            messages.success(request, f"Assigned {vehicle.make if vehicle else 'Unit'} / {driver.full_name if driver else 'Chauffeur'} to mission {req.request_number}.")

    elif action == 'onboard_provider':
        company_name = request.POST.get('company_name', '').strip()
        registration_number = request.POST.get('registration_number', '').strip()
        contact_person = request.POST.get('contact_person', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip().lower()
        address = request.POST.get('address', '').strip()
        service_area = request.POST.get('service_area', '').strip()
        specializations = request.POST.get('specializations', '').strip()
        status = request.POST.get('status', ProviderCompany.Status.APPROVED)
        rating_str = request.POST.get('overall_rating', '5.00').strip()

        if not company_name or not contact_person or not phone or not email:
            messages.error(request, "Company name, contact person, phone number, and dispatch email are required.")
            return redirect(redirect_target)

        if not registration_number:
            registration_number = f"DVLA-GH-{random.randint(10000, 99999)}"
        elif ProviderCompany.objects.filter(registration_number__iexact=registration_number).exists():
            messages.error(request, f"A transport provider with registration/permit number '{registration_number}' already exists.")
            return redirect(redirect_target)

        try:
            overall_rating = Decimal(rating_str)
        except Exception:
            overall_rating = Decimal('5.00')

        if status not in [ProviderCompany.Status.APPROVED, ProviderCompany.Status.PENDING, ProviderCompany.Status.SUSPENDED]:
            status = ProviderCompany.Status.APPROVED

        create_admin = request.POST.get('create_admin_account') in ['on', 'true', '1', True]
        admin_username = request.POST.get('admin_username', '').strip()
        admin_password = request.POST.get('admin_password', '').strip()

        with transaction.atomic():
            provider = ProviderCompany.objects.create(
                company_name=company_name,
                registration_number=registration_number,
                contact_person=contact_person,
                phone=phone,
                email=email,
                address=address or None,
                status=status,
                overall_rating=overall_rating,
                service_area=service_area or 'Greater Accra Region, Ghana',
                specializations=specializations or 'Executive Saloon, SUV, Airport Transfers'
            )

            admin_note = ""
            if create_admin:
                if not admin_username:
                    base_u = email.split('@')[0].replace('.', '_').replace('-', '_')
                    admin_username = base_u
                    suff = 1
                    while User.objects.filter(username__iexact=admin_username).exists():
                        admin_username = f"{base_u}_{suff}"
                        suff += 1

                if not admin_password:
                    admin_password = f"Flexy@{random.randint(1000, 9999)}!"

                existing_user = User.objects.filter(email__iexact=email).first()
                if existing_user:
                    existing_user.role = User.Role.PROVIDER_ADMIN
                    existing_user.is_verified = True
                    existing_user.save(update_fields=['role', 'is_verified'])
                    admin_note = f" (Existing user '{existing_user.username}' linked as Provider Admin)"
                else:
                    if User.objects.filter(username__iexact=admin_username).exists():
                        admin_username = f"{admin_username}_{random.randint(10, 99)}"

                    new_user = User.objects.create_user(
                        username=admin_username,
                        email=email,
                        first_name=contact_person,
                        role=User.Role.PROVIDER_ADMIN,
                        phone_number=phone,
                        is_verified=True,
                        password=admin_password
                    )
                    admin_note = f" (Admin account created: {new_user.username} / {admin_password})"

            messages.success(request, f"Transport Provider '{provider.company_name}' successfully onboarded.{admin_note}")

    elif action == 'update_provider':
        provider_id = request.POST.get('provider_id')
        provider = ProviderCompany.objects.filter(id=provider_id).first()
        if not provider:
            messages.error(request, "Transport provider not found.")
            return redirect(redirect_target)

        company_name = request.POST.get('company_name', '').strip()
        registration_number = request.POST.get('registration_number', '').strip()
        contact_person = request.POST.get('contact_person', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip().lower()
        address = request.POST.get('address', '').strip()
        service_area = request.POST.get('service_area', '').strip()
        specializations = request.POST.get('specializations', '').strip()
        status = request.POST.get('status', '').strip()
        rating_str = request.POST.get('overall_rating', '').strip()

        if company_name:
            provider.company_name = company_name
        if registration_number:
            if registration_number != provider.registration_number and ProviderCompany.objects.filter(registration_number__iexact=registration_number).exclude(id=provider.id).exists():
                messages.error(request, f"Permit/registration number '{registration_number}' is already registered to another provider.")
                return redirect(redirect_target)
            provider.registration_number = registration_number
        if contact_person:
            provider.contact_person = contact_person
        if phone:
            provider.phone = phone
        if email:
            provider.email = email
        if address is not None:
            provider.address = address
        if service_area is not None:
            provider.service_area = service_area
        if specializations is not None:
            provider.specializations = specializations
        if status in [ProviderCompany.Status.APPROVED, ProviderCompany.Status.PENDING, ProviderCompany.Status.SUSPENDED]:
            provider.status = status
        if rating_str:
            try:
                provider.overall_rating = Decimal(rating_str)
            except Exception:
                pass

        provider.save()
        messages.success(request, f"Provider profile for '{provider.company_name}' updated successfully.")

    elif action == 'toggle_provider_status':
        provider_id = request.POST.get('provider_id')
        new_status = request.POST.get('new_status')
        provider = ProviderCompany.objects.filter(id=provider_id).first()
        if provider and new_status in [ProviderCompany.Status.APPROVED, ProviderCompany.Status.PENDING, ProviderCompany.Status.SUSPENDED]:
            provider.status = new_status
            provider.save(update_fields=['status', 'updated_at'])
            if new_status == ProviderCompany.Status.APPROVED:
                messages.success(request, f"Transport Partner '{provider.company_name}' is now VERIFIED & APPROVED for wholesale RFQ broadcasts.")
            elif new_status == ProviderCompany.Status.SUSPENDED:
                messages.warning(request, f"Transport Partner '{provider.company_name}' has been SUSPENDED from bidding and dispatches.")
            else:
                messages.info(request, f"Transport Partner '{provider.company_name}' marked as PENDING review.")
        else:
            messages.error(request, "Invalid provider or status specified.")

    elif action == 'delete_provider':
        provider_id = request.POST.get('provider_id')
        provider = ProviderCompany.objects.filter(id=provider_id).first()
        if not provider:
            messages.error(request, "Transport provider not found.")
            return redirect(redirect_target)

        has_quotes = provider.quotes.exists()
        has_vehicles = provider.vehicles.exists()
        has_drivers = provider.drivers.exists()

        if has_quotes or has_vehicles or has_drivers:
            provider.status = ProviderCompany.Status.SUSPENDED
            provider.save(update_fields=['status', 'updated_at'])
            messages.warning(
                request,
                f"Provider '{provider.company_name}' has linked operational records ({provider.vehicles.count()} vehicles, {provider.drivers.count()} drivers, {provider.quotes.count()} quotes). Provider was SUSPENDED instead of deleted to protect historical audit data."
            )
        else:
            name = provider.company_name
            provider.delete()
            messages.success(request, f"Transport provider '{name}' has been permanently removed.")

    return redirect(redirect_target)


def handle_provider_post(request):
    """Handles mutation POST requests for provider operations."""
    provider_company = ProviderCompany.objects.filter(email=request.user.email).first()
    if not provider_company:
        provider_company = ProviderCompany.objects.first()

    action = request.POST.get('action')
    redirect_target = request.META.get('HTTP_REFERER') or 'portal_provider_workspace'

    if action == 'submit_quote':
        quote_req_id = request.POST.get('quote_request_id')
        offered_cost = request.POST.get('offered_cost', '0')
        proposed_vehicle_id = request.POST.get('proposed_vehicle_id')
        notes = request.POST.get('notes', '')

        pqr = ProviderQuoteRequest.objects.filter(id=quote_req_id, provider=provider_company).first()
        if pqr:
            veh = Vehicle.objects.filter(id=proposed_vehicle_id, provider=provider_company).first() if proposed_vehicle_id else None
            offered_dec = Decimal(offered_cost)
            pq, _ = ProviderQuote.objects.update_or_create(
                quote_request=pqr,
                provider=provider_company,
                defaults={
                    'offered_cost': offered_dec,
                    'proposed_vehicle': veh,
                    'notes': notes,
                    'status': ProviderQuote.Status.SUBMITTED
                }
            )
            pqr.status = ProviderQuoteRequest.Status.RESPONDED
            pqr.save()

            tier = CommissionTier.get_tier_for_request(pqr.request)
            if tier and tier.auto_dispatch_quote:
                margin_calc = offered_dec * (tier.margin_percentage / Decimal('100'))
                margin_amount = max(margin_calc, tier.min_margin_amount)
                final_price = offered_dec + margin_amount

                cq, _ = CustomerQuote.objects.update_or_create(
                    request=pqr.request,
                    defaults={
                        'selected_provider_quote': pq,
                        'provider_cost': offered_dec,
                        'margin_amount': margin_amount,
                        'final_customer_price': final_price,
                        'status': CustomerQuote.Status.SENT,
                        'created_by': request.user if request.user.is_authenticated else None,
                    }
                )
                pq.status = ProviderQuote.Status.ACCEPTED_BY_BROKER
                pq.save(update_fields=['status'])

                pqr.request.booking_status = 'QUOTE_AVAILABLE'
                pqr.request.save(update_fields=['booking_status'])

                send_quote_ready_email(cq, pqr.request)
                messages.success(request, f"Wholesale quote of GHS {offered_dec:,.0f} accepted! Customer quote auto-dispatched to client at GHS {final_price:,.0f}.")
            else:
                messages.success(request, f"Quote of GHS {offered_dec:,.0f} submitted to FlexyRide Broker Desk!")
        return redirect(redirect_target)

    elif action == 'decline_rfq':
        quote_req_id = request.POST.get('quote_request_id')
        pqr = ProviderQuoteRequest.objects.filter(id=quote_req_id, provider=provider_company).first()
        if pqr:
            pqr.status = ProviderQuoteRequest.Status.DECLINED
            pqr.save()
            messages.info(request, f"RFQ #{pqr.request.request_number} declined.")
        return redirect(redirect_target)

    elif action == 'add_vehicle':
        plate = request.POST.get('registration_number', '').strip().upper()
        make = request.POST.get('make', '').strip()
        model_name = request.POST.get('model', '').strip()
        year = request.POST.get('year', 2024)
        category = request.POST.get('category', Vehicle.Category.SUV)
        seating = request.POST.get('seating_capacity', 5)
        wifi = bool(request.POST.get('wifi_available'))
        water = bool(request.POST.get('water_provided'))
        color = request.POST.get('color', '').strip()
        luggage = request.POST.get('luggage_capacity', '').strip()
        accessibility = bool(request.POST.get('has_accessibility'))
        child_seat = bool(request.POST.get('has_child_seat'))

        if plate and make and model_name:
            Vehicle.objects.create(
                provider=provider_company,
                registration_number=plate,
                make=make,
                model=model_name,
                year=int(year) if year else 2024,
                category=category,
                seating_capacity=int(seating) if seating else 5,
                wifi_available=wifi,
                water_provided=water,
                color=color or None,
                luggage_capacity=luggage or None,
                has_accessibility=accessibility,
                has_child_seat=child_seat,
                status=Vehicle.Status.AVAILABLE,
                compliance_status=Vehicle.ComplianceStatus.COMPLIANT
            )
            messages.success(request, f"Vehicle {plate} ({make} {model_name}) added to fleet!")
        return redirect(redirect_target)

    elif action == 'edit_vehicle':
        vehicle_id = request.POST.get('vehicle_id')
        veh = Vehicle.objects.filter(id=vehicle_id, provider=provider_company).first()
        if veh:
            veh.make = request.POST.get('make', veh.make).strip()
            veh.model = request.POST.get('model', veh.model).strip()
            veh.year = int(request.POST.get('year', veh.year)) if request.POST.get('year') else veh.year
            veh.category = request.POST.get('category', veh.category)
            veh.seating_capacity = int(request.POST.get('seating_capacity', veh.seating_capacity))
            veh.wifi_available = bool(request.POST.get('wifi_available'))
            veh.water_provided = bool(request.POST.get('water_provided'))
            veh.color = request.POST.get('color', '').strip() or veh.color
            veh.luggage_capacity = request.POST.get('luggage_capacity', '').strip() or veh.luggage_capacity
            veh.has_accessibility = bool(request.POST.get('has_accessibility'))
            veh.has_child_seat = bool(request.POST.get('has_child_seat'))
            veh.save()
            messages.success(request, f"Vehicle {veh.registration_number} updated!")
        return redirect(redirect_target)

    elif action == 'add_driver':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone_number', '').strip()
        license_num = request.POST.get('license_number', '').strip().upper()
        languages = request.POST.get('languages_spoken', 'English, Twi, Ga').strip()
        license_expiry = request.POST.get('license_expiry')

        if full_name and phone and license_num:
            Driver.objects.create(
                provider=provider_company,
                full_name=full_name,
                phone_number=phone,
                license_number=license_num,
                languages_spoken=languages,
                license_expiry=license_expiry if license_expiry else None,
                status=Driver.Status.AVAILABLE,
                compliance_status=Driver.ComplianceStatus.COMPLIANT,
                rating=Decimal('4.90')
            )
            messages.success(request, f"Driver {full_name} enrolled successfully!")
        return redirect(redirect_target)

    elif action == 'edit_driver':
        driver_id = request.POST.get('driver_id')
        drv = Driver.objects.filter(id=driver_id, provider=provider_company).first()
        if drv:
            drv.full_name = request.POST.get('full_name', drv.full_name).strip()
            drv.phone_number = request.POST.get('phone_number', drv.phone_number).strip()
            drv.license_number = request.POST.get('license_number', drv.license_number).strip().upper()
            drv.languages_spoken = request.POST.get('languages_spoken', drv.languages_spoken).strip()
            license_expiry = request.POST.get('license_expiry')
            if license_expiry:
                drv.license_expiry = license_expiry
            drv.save()
            messages.success(request, f"Driver {drv.full_name} updated!")
        return redirect(redirect_target)

    elif action == 'update_company':
        company_name = request.POST.get('company_name', '').strip()
        contact_person = request.POST.get('contact_person', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        service_area = request.POST.get('service_area', '').strip()
        specializations = request.POST.get('specializations', '').strip()
        registration_number = request.POST.get('registration_number', '').strip()

        if company_name and provider_company:
            provider_company.company_name = company_name
            provider_company.contact_person = contact_person
            provider_company.phone = phone
            if email:
                provider_company.email = email
            provider_company.address = address
            provider_company.service_area = service_area
            provider_company.specializations = specializations
            if registration_number:
                provider_company.registration_number = registration_number
            provider_company.save()
            messages.success(request, "Company details updated successfully!")
        return redirect(redirect_target)

    elif action == 'update_vehicle_status':
        vehicle_id = request.POST.get('vehicle_id')
        new_status = request.POST.get('status')
        veh = Vehicle.objects.filter(id=vehicle_id, provider=provider_company).first()
        if veh and new_status:
            veh.status = new_status
            veh.save()
            messages.success(request, f"Vehicle {veh.registration_number} status updated to {veh.get_status_display()}!")
        return redirect(redirect_target)

    elif action == 'bulk_update_vehicle_status':
        vehicle_ids_raw = request.POST.get('vehicle_ids', '')
        new_status = request.POST.get('status')
        if vehicle_ids_raw and new_status:
            vids = [int(x.strip()) for x in vehicle_ids_raw.split(',') if x.strip().isdigit()]
            updated = Vehicle.objects.filter(id__in=vids, provider=provider_company).update(status=new_status)
            messages.success(request, f"Updated status for {updated} vehicles.")
        return redirect(redirect_target)

    elif action == 'update_driver_status':
        driver_id = request.POST.get('driver_id')
        new_status = request.POST.get('status')
        drv = Driver.objects.filter(id=driver_id, provider=provider_company).first()
        if drv and new_status:
            drv.status = new_status
            drv.save()
            messages.success(request, f"Driver {drv.full_name} status updated to {drv.get_status_display()}!")
        return redirect(redirect_target)

    elif action == 'update_trip_status':
        assignment_id = request.POST.get('assignment_id')
        new_status = request.POST.get('status')
        assignment = VehicleAssignment.objects.filter(id=assignment_id, vehicle__provider=provider_company).first()
        if assignment and new_status:
            assignment.status = new_status
            assignment.save()
            if new_status == VehicleAssignment.Status.COMPLETED:
                assignment.request.booking_status = TransportationRequest.BookingStatus.COMPLETED
                assignment.vehicle.status = Vehicle.Status.AVAILABLE
                assignment.driver.status = Driver.Status.AVAILABLE
                assignment.vehicle.save()
                assignment.driver.save()
            elif new_status == VehicleAssignment.Status.TRIP_IN_PROGRESS:
                assignment.request.booking_status = TransportationRequest.BookingStatus.TRIP_IN_PROGRESS
            elif new_status == VehicleAssignment.Status.ARRIVED:
                assignment.request.booking_status = TransportationRequest.BookingStatus.DRIVER_ARRIVED
            elif new_status == VehicleAssignment.Status.EN_ROUTE:
                assignment.request.booking_status = TransportationRequest.BookingStatus.DRIVER_EN_ROUTE
            assignment.request.save()
            messages.success(request, f"Trip #{assignment.request.request_number} status updated to {assignment.get_status_display()}!")
        return redirect(redirect_target)

    elif action == 'upload_compliance':
        doc_type = request.POST.get('document_type', ComplianceDocument.DocumentType.OTHER)
        doc_num = request.POST.get('document_number', '').strip()
        exp_date = request.POST.get('expiry_date')
        issue_date = request.POST.get('issue_date')
        ComplianceDocument.objects.create(
            provider=provider_company,
            target_type=ComplianceDocument.TargetType.PROVIDER,
            document_type=doc_type,
            document_number=doc_num,
            issue_date=issue_date if issue_date else None,
            expiry_date=exp_date if exp_date else None,
            status=ComplianceDocument.Status.APPROVED
        )
        messages.success(request, f"Compliance document {doc_num} uploaded and approved!")
        return redirect(redirect_target)

    elif action == 'update_admin_profile':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        if first_name and last_name and email:
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.email = email
            request.user.phone_number = phone_number
            request.user.save()
            messages.success(request, "Provider administrator profile details saved successfully!")
        else:
            messages.error(request, "First name, last name, and email are required.")
        return redirect(redirect_target)

    elif action == 'change_admin_password':
        curr_pw = request.POST.get('current_password', '')
        new_pw = request.POST.get('new_password', '')
        confirm_pw = request.POST.get('confirm_new_password', '')
        if not request.user.check_password(curr_pw):
            messages.error(request, "Current password entered is incorrect.")
        elif len(new_pw) < 6:
            messages.error(request, "New password must be at least 6 characters long.")
        elif new_pw != confirm_pw:
            messages.error(request, "New passwords do not match.")
        else:
            request.user.set_password(new_pw)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Password updated successfully!")
        return redirect(redirect_target)

    return redirect(redirect_target)

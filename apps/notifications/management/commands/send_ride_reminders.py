"""
Management command to scan and dispatch automated ride reminders (2 hours and 1 hour prior to pickup)
to all involved parties: Passenger, Corporate Requester/Booker, Assigned Chauffeur, and Fleet Provider.

Usage:
    python manage.py send_ride_reminders              # Live dispatch
    python manage.py send_ride_reminders --dry-run    # Preview upcoming eligible rides without sending
"""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from bookings.models import TransportationRequest
from notifications.email_service import send_ride_reminder_email


class Command(BaseCommand):
    help = "Dispatches pre-trip reminder emails (2h and 1h prior to pickup) to all involved parties."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview eligible upcoming scheduled rides without sending emails or updating timestamps.'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        now = timezone.now()

        self.stdout.write(self.style.NOTICE("================================================================="))
        self.stdout.write(self.style.NOTICE(f"FlexyRide Scheduled Ride Reminders Scan @ {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("MODE: DRY RUN (No emails will be dispatched)"))
        self.stdout.write(self.style.NOTICE("================================================================="))

        active_statuses = [
            TransportationRequest.BookingStatus.CONFIRMED,
            TransportationRequest.BookingStatus.ASSIGNED,
            TransportationRequest.BookingStatus.DRIVER_EN_ROUTE,
        ]

        # -------------------------------------------------------------
        # 1. Check 2-Hour Reminders (Target: between 1h15m and 2h15m ahead)
        # -------------------------------------------------------------
        two_hours_min = now + timedelta(minutes=75)
        two_hours_max = now + timedelta(hours=2, minutes=15)

        rides_2h = TransportationRequest.objects.filter(
            booking_status__in=active_statuses,
            departure_datetime__gte=two_hours_min,
            departure_datetime__lte=two_hours_max,
            reminder_2h_sent_at__isnull=True
        ).order_by('departure_datetime')

        self.stdout.write(self.style.WARNING(f"\n[1] 2-Hour Window ({two_hours_min.strftime('%H:%M')} -> {two_hours_max.strftime('%H:%M')}): {rides_2h.count()} ride(s) found."))

        count_2h = 0
        for ride in rides_2h:
            mins_until = int((ride.departure_datetime - now).total_seconds() / 60)
            primary_pass = ride.passengers.filter(is_primary=True).first() or ride.passengers.first()
            assignment = ride.vehicle_assignments.filter(status__in=['ASSIGNED', 'EN_ROUTE', 'ARRIVED']).first() or ride.vehicle_assignments.first()
            driver_name = assignment.driver.full_name if (assignment and assignment.driver) else "Unassigned"
            pass_name = primary_pass.full_name if primary_pass else "No passenger specified"

            self.stdout.write(f"  • Mission #{ride.request_number}: Departs in {mins_until} mins ({ride.departure_datetime.strftime('%H:%M')})")
            self.stdout.write(f"    Passenger: {pass_name} | Chauffeur: {driver_name} | Pickup: {ride.pickup_address[:45]}...")

            if not dry_run:
                try:
                    success = send_ride_reminder_email(ride, reminder_type='2h', async_send=False)
                    if success:
                        count_2h += 1
                        self.stdout.write(self.style.SUCCESS(f"    ✓ 2-Hour reminder dispatched to all involved parties."))
                    else:
                        self.stdout.write(self.style.ERROR(f"    ✗ Could not send 2-hour reminder (no recipient emails)."))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"    ✗ Error sending 2h reminder: {e}"))
            else:
                self.stdout.write(self.style.NOTICE(f"    [DRY RUN] Would dispatch 2-hour reminder email."))

        # -------------------------------------------------------------
        # 2. Check 1-Hour Reminders (Target: between now and 1h15m ahead)
        # -------------------------------------------------------------
        one_hour_min = now
        one_hour_max = now + timedelta(hours=1, minutes=15)

        rides_1h = TransportationRequest.objects.filter(
            booking_status__in=active_statuses,
            departure_datetime__gte=one_hour_min,
            departure_datetime__lte=one_hour_max,
            reminder_1h_sent_at__isnull=True
        ).order_by('departure_datetime')

        self.stdout.write(self.style.WARNING(f"\n[2] 1-Hour Window ({one_hour_min.strftime('%H:%M')} -> {one_hour_max.strftime('%H:%M')}): {rides_1h.count()} ride(s) found."))

        count_1h = 0
        for ride in rides_1h:
            mins_until = int((ride.departure_datetime - now).total_seconds() / 60)
            primary_pass = ride.passengers.filter(is_primary=True).first() or ride.passengers.first()
            assignment = ride.vehicle_assignments.filter(status__in=['ASSIGNED', 'EN_ROUTE', 'ARRIVED']).first() or ride.vehicle_assignments.first()
            driver_name = assignment.driver.full_name if (assignment and assignment.driver) else "Unassigned"
            pass_name = primary_pass.full_name if primary_pass else "No passenger specified"

            self.stdout.write(f"  • Mission #{ride.request_number}: Departs in {mins_until} mins ({ride.departure_datetime.strftime('%H:%M')})")
            self.stdout.write(f"    Passenger: {pass_name} | Chauffeur: {driver_name} | Pickup: {ride.pickup_address[:45]}...")

            if not dry_run:
                try:
                    success = send_ride_reminder_email(ride, reminder_type='1h', async_send=False)
                    if success:
                        count_1h += 1
                        self.stdout.write(self.style.SUCCESS(f"    ✓ 1-Hour reminder dispatched to all involved parties."))
                    else:
                        self.stdout.write(self.style.ERROR(f"    ✗ Could not send 1-hour reminder (no recipient emails)."))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"    ✗ Error sending 1h reminder: {e}"))
            else:
                self.stdout.write(self.style.NOTICE(f"    [DRY RUN] Would dispatch 1-hour reminder email."))

        self.stdout.write(self.style.NOTICE("\n================================================================="))
        if dry_run:
            self.stdout.write(self.style.NOTICE(f"Summary (DRY RUN): {rides_2h.count()} eligible for 2h reminder, {rides_1h.count()} eligible for 1h reminder."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Summary: Dispatched {count_2h} 2-hour reminders and {count_1h} 1-hour reminders successfully."))
        self.stdout.write(self.style.NOTICE("=================================================================\n"))


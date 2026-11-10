"""
Management command to run scheduled background jobs manually or via cron.
Runs:
1. Recurring bookings generation (bookings.tasks.generate_recurring_bookings_task)
2. Compliance document expiration warnings (compliance.tasks.check_document_expirations_task)
3. SLA breach detection (sla.tasks.detect_sla_breaches_task)
4. Pre-trip ride reminders (2h and 1h prior to pickup) (notifications.tasks.dispatch_ride_reminders_task)
"""

from django.core.management.base import BaseCommand
from bookings.tasks import generate_recurring_bookings_task
from compliance.tasks import check_document_expirations_task
from sla.tasks import detect_sla_breaches_task
from notifications.tasks import dispatch_ride_reminders_task


class Command(BaseCommand):
    help = "Executes scheduled operational jobs (Recurring bookings, Compliance warnings, SLA breaches, Ride reminders)."

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Execute all scheduled tasks (default)')
        parser.add_argument('--recurring', action='store_true', help='Run recurring booking generation only')
        parser.add_argument('--compliance', action='store_true', help='Run compliance document check only')
        parser.add_argument('--sla', action='store_true', help='Run SLA breach detection only')
        parser.add_argument('--reminders', action='store_true', help='Run 2h and 1h pre-trip ride reminders only')

    def handle(self, *args, **options):
        run_all = options['all'] or not (options['recurring'] or options['compliance'] or options['sla'] or options['reminders'])

        self.stdout.write(self.style.NOTICE("=== Starting FlexyRide Scheduled Operational Workers ==="))

        if run_all or options['recurring']:
            self.stdout.write(self.style.WARNING("\n[1/4] Running Recurring Bookings Generation..."))
            try:
                res_rec = generate_recurring_bookings_task()
                self.stdout.write(self.style.SUCCESS(f"  ✓ Generated {res_rec['generated_count']} recurring booking occurrences."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed recurring bookings: {e}"))

        if run_all or options['compliance']:
            self.stdout.write(self.style.WARNING("\n[2/4] Running Compliance Document Expiration Checks..."))
            try:
                res_comp = check_document_expirations_task()
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Sent {res_comp['notices_sent']} renewal notices; {res_comp['expired_lockouts']} expired units locked out."
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed compliance check: {e}"))

        if run_all or options['sla']:
            self.stdout.write(self.style.WARNING("\n[3/4] Running SLA Breach Detection..."))
            try:
                res_sla = detect_sla_breaches_task()
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Processed: {res_sla['breaches_detected']} breaches detected "
                    f"({res_sla['slow_rfqs_count']} RFQ timeouts, {res_sla['unassigned_urgent_count']} unassigned urgent trips, "
                    f"{res_sla['delayed_chauffeurs_count']} delayed arrivals)."
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed SLA detection: {e}"))

        if run_all or options['reminders']:
            self.stdout.write(self.style.WARNING("\n[4/4] Running Pre-Trip Ride Reminders (2h & 1h prior)..."))
            try:
                res_rem = dispatch_ride_reminders_task()
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Dispatched {res_rem['reminders_2h_sent']} 2-hour reminders and {res_rem['reminders_1h_sent']} 1-hour reminders to involved parties."
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed ride reminders: {e}"))

        self.stdout.write(self.style.NOTICE("\n=== Completed FlexyRide Scheduled Jobs ===\n"))

        self.stdout.write(self.style.NOTICE("\n=== Completed FlexyRide Scheduled Jobs ===\n"))

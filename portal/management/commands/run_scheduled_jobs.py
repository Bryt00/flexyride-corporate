"""
Management command to run scheduled background jobs manually or via cron.
Runs:
1. Recurring bookings generation (bookings.tasks.generate_recurring_bookings_task)
2. Compliance document expiration warnings (compliance.tasks.check_document_expirations_task)
3. SLA breach detection (sla.tasks.detect_sla_breaches_task)
"""

from django.core.management.base import BaseCommand
from bookings.tasks import generate_recurring_bookings_task
from compliance.tasks import check_document_expirations_task
from sla.tasks import detect_sla_breaches_task


class Command(BaseCommand):
    help = "Executes scheduled operational jobs (Recurring bookings, Compliance warnings, SLA breaches)."

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Execute all scheduled tasks (default)')
        parser.add_argument('--recurring', action='store_true', help='Run recurring booking generation only')
        parser.add_argument('--compliance', action='store_true', help='Run compliance document check only')
        parser.add_argument('--sla', action='store_true', help='Run SLA breach detection only')

    def handle(self, *args, **options):
        run_all = options['all'] or not (options['recurring'] or options['compliance'] or options['sla'])

        self.stdout.write(self.style.NOTICE("=== Starting FlexyRide Scheduled Operational Workers ==="))

        if run_all or options['recurring']:
            self.stdout.write(self.style.WARNING("\n[1/3] Running Recurring Bookings Generation..."))
            try:
                res_rec = generate_recurring_bookings_task()
                self.stdout.write(self.style.SUCCESS(f"  ✓ Generated {res_rec['generated_count']} recurring booking occurrences."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed recurring bookings: {e}"))

        if run_all or options['compliance']:
            self.stdout.write(self.style.WARNING("\n[2/3] Running Compliance Document Expiration Checks..."))
            try:
                res_comp = check_document_expirations_task()
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Sent {res_comp['notices_sent']} renewal notices; {res_comp['expired_lockouts']} expired units locked out."
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed compliance check: {e}"))

        if run_all or options['sla']:
            self.stdout.write(self.style.WARNING("\n[3/3] Running SLA Breach Detection..."))
            try:
                res_sla = detect_sla_breaches_task()
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Processed: {res_sla['breaches_detected']} breaches detected "
                    f"({res_sla['slow_rfqs_count']} RFQ timeouts, {res_sla['unassigned_urgent_count']} unassigned urgent trips, "
                    f"{res_sla['delayed_chauffeurs_count']} delayed arrivals)."
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed SLA detection: {e}"))

        self.stdout.write(self.style.NOTICE("\n=== Completed FlexyRide Scheduled Jobs ===\n"))

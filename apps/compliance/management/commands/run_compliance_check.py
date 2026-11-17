from django.core.management.base import BaseCommand
from compliance.tasks import check_document_expirations_task


class Command(BaseCommand):
    help = "Executes compliance document expiration check and applies booking lockouts"

    def handle(self, *args, **options):
        self.stdout.write("Running compliance document expiration monitoring...")
        result = check_document_expirations_task()
        self.stdout.write(
            self.style.SUCCESS(
                f"Compliance scan completed successfully: "
                f"{result['notices_sent']} notice(s) sent, "
                f"{result['expired_lockouts']} expired lockout(s) applied."
            )
        )


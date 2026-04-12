from django.core.management.base import BaseCommand
from machine_learning.models import FaceEnrollment, FaceScanAudit

class Command(BaseCommand):
    help = 'Deletes all face enrollment and scan audit records from the database.'

    def handle(self, *args, **options):
        enrollment_count = FaceEnrollment.objects.count()
        audit_count = FaceScanAudit.objects.count()

        FaceEnrollment.objects.all().delete()
        FaceScanAudit.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {enrollment_count} FaceEnrollment records.'))
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {audit_count} FaceScanAudit records.'))
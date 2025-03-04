from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from ddm.participation.models import Participant


class CleanParticipants(BaseCommand):
    help = (
        'Deletes participants that have started participation over 180 days '
        'ago and did not explicitly consent to donating their data for '
        'academic research.'
    )

    def handle(self, *args, **options):
        ref_datetime = timezone.now() - timedelta(days=180)
        participants_to_delete = Participant.objects.filter(
            start_time__lt=ref_datetime,
            # TODO: Check for donation consent.
        )
        n_participants = participants_to_delete.count()
        participants_to_delete.delete()

        self.stdout.write(self.style.SUCCESS(f'Deleted {n_participants}'))

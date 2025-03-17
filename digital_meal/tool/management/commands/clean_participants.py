from datetime import timedelta

from ddm.datadonation.models import DataDonation
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from ddm.participation.models import Participant


# TODO: Complete function once the questionnaire has been defined.
class CleanParticipants(BaseCommand):
    help = (
        'Deletes donations of participants that have started participation over 180 days '
        'ago and did not explicitly consent to donating their data for '
        'academic research.'
    )

    def handle(self, *args, **options):
        ref_datetime = timezone.now() - timedelta(days=180)
        participants_to_delete = Participant.objects.filter(
            start_time__lt=ref_datetime,
            # TODO: More efficient filtering (could also directly filter based on responses).
        )

        # Get questionnaire responses
        participants_wo_consent = 0
        responses = []  # TODO: Get responses queryset.
        for response in responses:
            response_data = None  # response.get_decrypted_data(project.secret, project.get_salt())
            consent = response_data.get('consent_variable', True)
            if consent:
                continue
            participants_wo_consent += 1

            participant = response.participant
            donations = DataDonation.objects.filter(participant=participant)
            donations.delete()

        self.stdout.write(self.style.SUCCESS(f'Deleted responses of {len(participants_wo_consent)} participants.'))

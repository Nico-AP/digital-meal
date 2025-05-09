from datetime import timedelta

from django.conf import settings
from ddm.datadonation.models import DataDonation
from ddm.logging.models import ExceptionLogEntry, ExceptionRaisers
from ddm.projects.models import DonationProject
from ddm.questionnaire.models import QuestionnaireResponse
from django.core.management.base import BaseCommand
from django.utils import timezone
from ddm.participation.models import Participant


def delete_donations(participant: Participant, project: DonationProject) -> None:
    """
    Deletes all donations by the provided participant.

    :param participant: A Participant instance for which the donation should be deleted.
    :param project: A DonationProject instance to which the donation to be deleted belongs.
    :return: None
    """
    donations = DataDonation.objects.filter(
        participant=participant,
        project=project
    )
    donations.delete()
    return


def create_job_logs(cleaning_stats: dict) -> None:
    """
    Tries to create a log in the DDM project

    Fails silently.

    :param cleaning_stats: A dictionary holding the cleaning statistics as:
        {'<project.pk>: {
            'project': <project>,
            'n_checked': <int>,
            'n_deleted': <int>
        }}
    :return: None
    """
    for project_pk, stats in cleaning_stats.items():
        message = (
            f'Checked {stats["n_checked"]} participants. '
            f'{stats["n_deleted"]} donations were deleted due to missing consent.'
        )

        try:
            ExceptionLogEntry.objects.create(
                date=timezone.now(),
                project=stats.project,
                uploader=None,
                blueprint=None,
                raised_by=ExceptionRaisers.SERVER,
                exception_type='CRONJOB PARTICIPANT CLEANING',
                message=message
            )
        except:
            pass
    return


def initialize_cleaning_stats() -> dict:
    """
    Initializes a dictionary to record cleaning statistics. Creates an
    entry for every project that currently exists.

    :return: A dictionary holding the cleaning statistics as:
        {'<project.pk>: {
            'project': <project>,
            'n_checked': 0,
            'n_deleted': 0
        }}
    """
    cleaning_stats = {}
    projects = DonationProject.objects.all()
    for project in projects:
        cleaning_stats[project.pk] = {
            'project': project.pk,
            'n_checked': 0,
            'n_deleted': 0
        }
    return cleaning_stats


class Command(BaseCommand):
    """
    Deletes donations of participants that have started participation over x days
    ago (defined in a DAYS_TO_DONATION_DELETION setting) and did not explicitly
    consent to donating their data for academic research.

    It is expected that explicitly consent is recorded in the questionnaire in
    a variable called "dd_consent" that equals 1 if consent is given.

    This function is intended to be called daily as a cron job.
    """

    help = (
        'Deletes donations of participants that have started participation '
        'over x days ago and not provided explicit consent to store their data.'
    )

    def handle(self, *args, **options):
        ref_datetime = timezone.now() - timedelta(days=settings.DAYS_TO_DONATION_DELETION)
        participants_to_check = Participant.objects.filter(
            start_time__date=ref_datetime.date(),
        )
        participants_to_delete = []
        cleaning_stats = initialize_cleaning_stats()

        for participant in participants_to_check:
            responses = QuestionnaireResponse.objects.filter()

            for response in responses:
                project = response.project
                cleaning_stats[project.pk]['n_checked'] += 1

                # Check consent.
                response_data = response.get_decrypted_data(
                    project.secret, project.get_salt())
                consent = response_data.get('dd_consent')
                if consent == 1:
                    continue

                participants_to_delete.append(participant.pk)
                delete_donations(participant, project)
                cleaning_stats[project.pk]['n_deleted'] += 1

        # Delete participants.
        Participant.objects.filter(pk__in=participants_to_delete).delete()

        # Create project logs in ddm.
        create_job_logs(cleaning_stats)

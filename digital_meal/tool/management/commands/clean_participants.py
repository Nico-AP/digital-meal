import logging_utils
from datetime import timedelta

from ddm.apis.serializers import ResponseSerializer
from django.conf import settings
from ddm.datadonation.models import DataDonation
from ddm.logging.models import ExceptionLogEntry, ExceptionRaisers
from ddm.projects.models import DonationProject
from ddm.questionnaire.models import QuestionnaireResponse
from django.core.management.base import BaseCommand
from django.utils import timezone
from ddm.participation.models import Participant


logger = logging.getLogger(__name__)


def delete_donations(participant: Participant, project: DonationProject) -> None:
    """
    Deletes all donations by the provided participant.

    Args:
        participant: A Participant instance for which the donation should be deleted.
        project: A DonationProject instance to which the donation to be deleted belongs.

    Returns:
        None
    """
    donations = DataDonation.objects.filter(
        participant=participant,
        project=project
    )
    donations.delete()
    return


def delete_response(participant: Participant, project: DonationProject) -> None:
    """

    Args:
        participant: A Participant instance for which the response should be deleted.
        project: A DonationProject instance to which the response to be deleted belongs.

    Returns:
        None
    """
    responses = QuestionnaireResponse.objects.filter(
        participant=participant,
        project=project
    )
    responses.delete()
    return


def create_job_logs(cleaning_stats: dict) -> None:
    """
    Tries to create a log in the DDM project

    Fails silently.

    Args:
        cleaning_stats: A dictionary holding the cleaning statistics as:
            {'<project.pk>: {
                'project': <project>,
                'n_donations_deleted': 0,
                'n_responses_deleted': 0,
                'n_miss_usage_consent_var': 0,
                'n_miss_quest_consent_var': 0
            }}

    Returns:
        None
    """
    for project_pk, stats in cleaning_stats.items():
        message = (
            f'Checked {stats["n_checked"]} participants.\n'
            f'{stats["n_donations_deleted"]} donations were deleted due to missing consent.\n'
            f'{stats["n_responses_deleted"]} questionnaire responses were deleted due to missing consent.\n'
            f'{stats["n_miss_usage_consent_var"]} cases were missing the usage data consent variable.\n'
            f'{stats["n_miss_quest_consent_var"]} cases were missing the questionnaire consent variable.'
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

    Returns:
        A dictionary holding the cleaning statistics as.
    """
    cleaning_stats = {}
    projects = DonationProject.objects.all()
    for project in projects:
        cleaning_stats[project.pk] = {
            'project': project.pk,
            'n_checked': 0,
            'n_donations_deleted': 0,
            'n_responses_deleted': 0,
            'n_miss_usage_consent_var': 0,
            'n_miss_quest_consent_var': 0
        }
    return cleaning_stats


# TODO: Test again thoroughly
# TODO: Differentiate between donations and responses.
# TODO: Handle test cases (delete 30 days after participation).
class Command(BaseCommand):
    """
    Deletes donations of participants that have started participation over x days
    ago (defined in a DAYS_TO_DONATION_DELETION setting) and did not explicitly
    consent to donating their data for academic research.

    It is expected that explicit consent is recorded in the questionnaire in
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
        cleaning_stats = initialize_cleaning_stats()

        for participant in participants_to_check:
            responses = QuestionnaireResponse.objects.filter(participant=participant)

            if len(responses) > 1:
                logger.warning(
                    'Clean Participant Command: Found more than one response for participant: %s',
                    participant.external_id
                )
                continue

            response = responses.first()
            serialized_response = ResponseSerializer(response).data

            response_data = serialized_response.get('response_data')
            if not response_data:
                logger.warning(
                    'Clean Participant Command: Encountered response with no response_data for participant: %s',
                    participant.external_id
                )
                continue

            project = response.project
            cleaning_stats[project.pk]['n_checked'] += 1

            # Check consent for usage data donation.
            usage_dd_consent = response_data.get('usage_dd_consent')
            if usage_dd_consent is None:
                cleaning_stats[project.pk]['n_miss_usage_consent_var'] += 1
                logger.warning(
                    'Clean Participant Command: Encountered response with missing "usage_dd_consent" variable '
                    'for participant: %s',
                    participant.external_id
                )
            elif usage_dd_consent not in [1, '1']:
                delete_donations(participant, project)
                cleaning_stats[project.pk]['n_donations_deleted'] += 1

            # Check consent for questionnaire response donation.
            quest_consent = response_data.get('quest_dd_consent')
            if quest_consent is None:
                logger.warning(
                    'Clean Participant Command: Encountered response with missing "quest_dd_consent" variable '
                    'for participant: %s',
                    participant.external_id
                )
            elif quest_consent not in [1, '1']:
                delete_response(participant, project)
                cleaning_stats[project.pk]['n_responses_deleted'] += 1

        # Create project logs in ddm.
        create_job_logs(cleaning_stats)

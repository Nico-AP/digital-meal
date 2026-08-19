from ddm.datadonation.models import DataDonation, DonationBlueprint
from ddm.participation.models import Participant
from ddm.projects.models import DonationProject
from django.conf import settings
from django.urls import NoReverseMatch, reverse

from mydigitalmeal.datadonation.constants import (
    TIKTOK_PROJECT_SLUG,
    TIKTOK_WATCH_HISTORY_BP_NAME,
)


def get_tiktok_project() -> DonationProject:
    """Returns project or raises exception"""
    return DonationProject.objects.get(slug=TIKTOK_PROJECT_SLUG)


def get_tiktok_wh_bp(project_id: int | None) -> DonationBlueprint:
    """Returns blueprint or raises exception"""
    return DonationBlueprint.objects.get(
        project__id=project_id or get_tiktok_project(),
        name=TIKTOK_WATCH_HISTORY_BP_NAME,
    )


def get_tiktok_wh_data(participant: Participant, ddm_project_id: int | None):
    """Loads the data donation associated with the DDM watch history blueprint
    for a given participant.
    """
    if not ddm_project_id:
        ddm_project = get_tiktok_project()
    else:
        ddm_project = DonationProject.objects.get(pk=ddm_project_id)
    blueprint = get_tiktok_wh_bp(ddm_project_id)

    try:
        data_donation = DataDonation.objects.get(
            project__pk=ddm_project_id,
            blueprint=blueprint,
            participant=participant,
            data_extraction_state=DataDonation.DataExtractionState.DATA_EXTRACTED,
        )
    except DataDonation.DoesNotExist:
        return None

    return data_donation.get_decrypted_data(ddm_project.secret, ddm_project.get_salt())


def get_step_url(steps: list[str], current_step: int, slug: str | None) -> str:
    """Defensive resolution of url, allowing for both urls that need and
    do not need slug-kwarg.
    """
    if slug is None:
        slug = settings.TIKTOK_DDM_PROJECT_SLUG

    try:
        return reverse(steps[current_step], kwargs={"slug": slug})
    except NoReverseMatch:
        # Fallback for URLs hard-coding the "tiktok" slug.
        return reverse(steps[current_step])


def get_current_step_url(steps: list[str], current_step: int, slug: str | None) -> str:
    """Defensive resolution of current step url, allowing for both urls that need
    and do not need slug-kwarg.
    """
    return get_step_url(steps, current_step, slug)


def get_next_step_url(steps: list[str], current_step: int, slug: str | None) -> str:
    """Defensive resolution of next step url, allowing for both urls that need and
    do not need slug-kwarg.
    """
    current_step += 1
    return get_step_url(steps, current_step, slug)

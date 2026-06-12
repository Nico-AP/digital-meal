from ddm.datadonation.models import DataDonation, DonationBlueprint
from ddm.participation.models import Participant
from ddm.projects.models import DonationProject

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

    donated_data = DataDonation.objects.get(
        project__pk=ddm_project_id,
        blueprint=blueprint,
        participant=participant,
    )

    # TODO: Implement status check here once this has been better implemented in DDM

    return donated_data.get_decrypted_data(ddm_project.secret, ddm_project.get_salt())

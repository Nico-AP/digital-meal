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


def get_tiktok_wh_bp(project: DonationProject | None) -> DonationBlueprint:
    """Returns blueprint or raises exception"""
    return DonationBlueprint.objects.get(
        project=project or get_tiktok_project(),
        name=TIKTOK_WATCH_HISTORY_BP_NAME,
    )


def get_tiktok_wh_data(participant: Participant):
    project = get_tiktok_project()
    blueprint = get_tiktok_wh_bp(project)

    donated_data = DataDonation.objects.get(
        project=project,
        blueprint=blueprint,
        participant=participant,
    )

    # TODO: Implement status check here once this has been better implemented in DDM

    return donated_data.get_decrypted_data(project.secret, project.get_salt())

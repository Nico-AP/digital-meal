import json
import logging
import zipfile
from json import JSONDecodeError

from celery import group
from ddm.datadonation.models import DonationBlueprint
from ddm.logging.utils import log_server_exception
from ddm.participation.views import DataDonationView, create_participation_session
from ddm.projects.models import DonationProject
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.datastructures import MultiValueDictKeyError

from mydigitalmeal.datadonation.constants import (
    TIKTOK_PROJECT_SLUG,
    TIKTOK_WATCH_HISTORY_BP_NAME,
)
from mydigitalmeal.profiles.mixins import LoginAndProfileRequiredMixin
from mydigitalmeal.profiles.models import MDMProfile
from mydigitalmeal.statistics.models import StatisticsRequest, StatisticsScope
from mydigitalmeal.statistics.tasks import compute_tiktok_wh_statistics_from_donation
from mydigitalmeal.userflow.constants import URLShortcut
from mydigitalmeal.userflow.sessions import AddUserflowSessionMixin

logger = logging.getLogger(__name__)


class DonationViewDDM(
    LoginAndProfileRequiredMixin, AddUserflowSessionMixin, DataDonationView
):
    template_name = "datadonation/base_ddm.html"
    step_name = URLShortcut.DONATION_DDM
    steps = [
        URLShortcut.OVERVIEW,
        URLShortcut.DONATION_DDM,
        URLShortcut.QUESTIONNAIRE,
        URLShortcut.REPORT,
    ]

    def _initialize_values(self, request):
        """Overwrite project initialization and current step assignment"""
        try:
            self.object = DonationProject.objects.get(slug=TIKTOK_PROJECT_SLUG)
        except DonationProject.DoesNotExist as e:
            raise Http404 from e

        create_participation_session(request, self.object)
        self.participant = self.get_participant_from_session(request)
        if self.participant.current_step is None or self.participant.current_step < 1:
            self.participant.current_step = 1
            self.participant.start_time = timezone.now()
            self.participant.save()

        # Update DDM step
        self.current_step = self.participant.current_step

    def get(self, request, *args, **kwargs):
        """Overwritten to adjust redirect urls."""

        # Check if project is active.
        if not self.object.active:
            return redirect("ddm_participation:project_inactive", slug=self.object.slug)

        # Redirect to previous step if necessary.
        if self.steps[self.current_step] != self.step_name:
            return redirect(self.steps[self.current_step])

        # Render current view.
        context = self.get_context_data(object=self.object)
        self.extra_before_render(request)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        # Account for 'page back' action in browser
        if self.steps[self.current_step] != self.step_name:
            return redirect(self.steps[self.current_step])

        self.process_uploads(request.FILES)
        self.set_step_completed()
        redirect_url = reverse(URLShortcut.QUESTIONNAIRE)
        return HttpResponseRedirect(redirect_url)

    def process_uploads(self, files):
        try:
            file = files["post_data"]
        except (MultiValueDictKeyError, KeyError) as e:
            msg = (
                "Data Donation Processing Exception: Did not receive "
                f"expected data file from client. {e}"
            )
            log_server_exception(self.object, msg)
            return

        if not zipfile.is_zipfile(file):
            msg = (
                "Data Donation Processing Exception: Data file received "
                "from client is not a zip file."
            )
            log_server_exception(self.object, msg)
            return

        # Check if zip file contains expected file.
        unzipped_file = zipfile.ZipFile(file, "r")
        if "data_donation.json" not in unzipped_file.namelist():
            msg = (
                "Data Donation Processing Exception: "
                "'data_donation.json' is not in namelist."
            )
            log_server_exception(self.object, msg)
            return

        # Process donation data.
        try:
            file_data = json.loads(
                unzipped_file.read("data_donation.json").decode("utf-8"),
            )
        except UnicodeDecodeError:
            try:
                file_data = json.loads(
                    unzipped_file.read("data_donation.json").decode("latin-1"),
                )
            except ValueError:
                msg = (
                    "Donated data could not be decoded - "
                    "tried utf-8 and latin-1 decoding."
                )
                log_server_exception(self.object, msg)
                return
        except JSONDecodeError:
            msg = "JSON decode error in donated data."
            log_server_exception(self.object, msg)
            return

        for upload in file_data:
            blueprint_id = upload
            blueprint_data = file_data[upload]
            try:
                blueprint = DonationBlueprint.objects.get(
                    pk=blueprint_id,
                    project=self.object,
                )
            except DonationBlueprint.DoesNotExist:
                msg = (
                    "Data Donation Processing Exception: Referenced "
                    f"blueprint with id={blueprint_id} does not exist for "
                    "this project."
                )
                log_server_exception(self.object, msg)
                return

            if blueprint.name == TIKTOK_WATCH_HISTORY_BP_NAME:
                self.validate_received_data(blueprint, blueprint_data)

            blueprint.process_donation(blueprint_data, self.participant)

        # Added this:
        self.initialize_statistic_computation(file_data)

    def initialize_statistic_computation(self):
        # TODO: Optimize this logic
        statistics_request_interval = self.initialize_statistics_request()
        statistics_request_full = self.initialize_statistics_request()
        self.userflow_session.update(
            statistics_requested=True, request_id=statistics_request_interval.public_id
        )

        job = group(
            compute_tiktok_wh_statistics_from_donation.s(
                statistics_request_id=statistics_request_full.pk,
                statistics_scope=StatisticsScope.FULL,
            ),
            compute_tiktok_wh_statistics_from_donation.s(
                statistics_request_id=statistics_request_interval.pk,
                statistics_scope=StatisticsScope.INTERVAL,
            ),
        )
        transaction.on_commit(job.delay)

        logger.info(
            "Scheduled statistics computation for participant %s.",
            self.participant.pk,
        )

    def initialize_statistics_request(self) -> StatisticsRequest:
        user = self.request.user
        profile = MDMProfile.objects.get(user=user)
        return StatisticsRequest.objects.create(
            profile=profile,
            participant=self.participant,
        )

    def validate_received_data(self, wh_blueprint, wh_data) -> bool:
        if not self.validate_watch_history_data(wh_blueprint, wh_data):
            return False

        if not self.validate_donation_consent(wh_data.get("consent")):
            return False

        return self.validate_donation_status(wh_data.get("status"))

    def validate_watch_history_data(
        self, wh_blueprint: DonationBlueprint, wh_data: dict
    ) -> bool:
        if not wh_data:
            return False
        if not wh_blueprint.validate_donation(wh_data):
            msg = (
                "Received invalid watch history donation "
                f"(participant: {self.participant.pk})"
            )
            logger.error(msg)
            return False
        return True

    def validate_donation_consent(self, consent_value: bool) -> bool:
        if not consent_value:
            msg = (
                "Received donation without consent (None) for watch history data "
                f"(participant: {self.participant.pk}"
            )
            logger.info(msg)
            return False
        return True

    def validate_donation_status(self, status_value: str) -> bool:
        if status_value in ["failed", "pending", "no data extracted"]:
            msg = (
                f"Received invalid donation with status: {status_value} "
                f"(participant: {self.participant.pk})"
            )
            logger.info(msg)
            return False
        return True

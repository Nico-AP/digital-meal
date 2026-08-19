import logging

from celery import group
from ddm.participation.views import DataDonationView, create_participation_session
from ddm.projects.models import DonationProject
from django.db import transaction
from django.db.models import QuerySet
from django.http import Http404, HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from mydigitalmeal.datadonation.constants import TIKTOK_PROJECT_SLUG
from mydigitalmeal.datadonation.utils import get_current_step_url, get_next_step_url
from mydigitalmeal.profiles.mixins import LoginAndProfileRequiredMixin
from mydigitalmeal.profiles.models import MDMProfile
from mydigitalmeal.statistics.models import StatisticsRequest, StatisticsScope
from mydigitalmeal.statistics.tasks import compute_tiktok_wh_statistics_from_donation
from mydigitalmeal.userflow.constants import URLShortcut
from mydigitalmeal.userflow.sessions import AddUserflowSessionMixin

logger = logging.getLogger(__name__)


class BaseDonationViewDDM(AddUserflowSessionMixin, DataDonationView):
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
        self.object = self.get_object()

        create_participation_session(request, self.object)
        self.participant = self.get_participant_from_session(request)
        if self.participant.current_step is None or self.participant.current_step < 1:
            self.participant.current_step = 1
            self.participant.start_time = timezone.now()
            self.participant.save()

        self.update_participant_information(request)

        # Update DDM step
        self.current_step = self.participant.current_step

    def get_object(self, queryset: QuerySet | None = None) -> DonationProject:
        try:
            return DonationProject.objects.get(slug=TIKTOK_PROJECT_SLUG)
        except DonationProject.DoesNotExist as e:
            raise Http404 from e

    def current_step_url(self) -> str:
        return get_current_step_url(self.steps, self.current_step, self.object.slug)

    def next_step_url(self) -> str:
        return get_next_step_url(self.steps, self.current_step, self.object.slug)

    def update_participant_information(self, request) -> None:
        """Placeholder function."""
        return

    def post_redirect_url(self) -> str:
        return reverse(URLShortcut.QUESTIONNAIRE)

    def post(self, request: HttpRequest, *args, **kwargs):
        # Account for 'page back' action in browser
        if self.steps[self.current_step] != self.step_name:
            return redirect(self.current_step_url())

        self.process_uploads(request.FILES)
        self.set_step_completed()
        return HttpResponseRedirect(self.post_redirect_url())

    def process_blueprints(self, file_data: dict[str, dict]) -> None:
        """Overwrite to add statistics computation initialization."""
        super().process_blueprints(file_data)
        self.initialize_statistic_computation()

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
                ddm_project_id=self.object.pk,
            ),
            compute_tiktok_wh_statistics_from_donation.s(
                statistics_request_id=statistics_request_interval.pk,
                statistics_scope=StatisticsScope.INTERVAL,
                ddm_project_id=self.object.pk,
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


class DonationViewDDM(LoginAndProfileRequiredMixin, BaseDonationViewDDM):
    """Adds Login required to donation view for standard My Digital Meal flow."""

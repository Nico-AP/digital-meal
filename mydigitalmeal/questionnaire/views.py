from ddm.participation.views import QuestionnaireView
from ddm.projects.models import DonationProject
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse

from mydigitalmeal.datadonation.constants import TIKTOK_PROJECT_SLUG
from mydigitalmeal.datadonation.utils import get_current_step_url
from mydigitalmeal.profiles.mixins import LoginAndProfileRequiredMixin
from mydigitalmeal.userflow.constants import URLShortcut


class MDMQuestionnaireView(LoginAndProfileRequiredMixin, QuestionnaireView):
    template_name = "mdm_questionnaire/questionnaire.html"
    step_name = URLShortcut.QUESTIONNAIRE
    steps = [
        URLShortcut.OVERVIEW,
        URLShortcut.DONATION_DDM,
        URLShortcut.QUESTIONNAIRE,
        URLShortcut.REPORT,
    ]

    def get_object(self, queryset=None):
        """Only render questionnaire for specific object."""
        try:
            return DonationProject.objects.get(slug=TIKTOK_PROJECT_SLUG)
        except DonationProject.DoesNotExist as e:
            raise Http404 from e

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["project_slug"] = TIKTOK_PROJECT_SLUG
        return context

    def current_step_url(self) -> str:
        return get_current_step_url(self.steps, self.current_step, self.object.slug)

    def next_step_url(self) -> str:
        return reverse(URLShortcut.REPORT)

    def post(self, request, *args, **kwargs):
        """Overwrite to redirect to report view."""
        super().post(request, **kwargs)

        # TODO: Likely not needed here as already called in parent:
        self.process_response(request.POST)
        return HttpResponseRedirect(reverse(URLShortcut.REPORT))

from ddm.participation.views import QuestionnaireView
from ddm.projects.models import DonationProject
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse

from mydigitalmeal.datadonation.constants import TIKTOK_PROJECT_SLUG
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

    def get(self, request, *args, **kwargs):
        """Overwrite to control redirect targets."""
        # Redirect to previous step if necessary.
        if self.steps[self.current_step] != self.step_name:
            return redirect(self.steps[self.current_step])

        context = self.get_context_data(object=self.object)
        min_config_length = 2
        if not len(context["q_config"]) > min_config_length:
            self.set_step_completed()
            return HttpResponseRedirect(reverse(URLShortcut.REPORT))
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        """Overwrite to redirect to report view."""
        super().post(request, **kwargs)
        self.process_response(request.POST)
        return HttpResponseRedirect(reverse(URLShortcut.REPORT))

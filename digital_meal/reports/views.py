import json

from ddm.datadonation.models import DonationBlueprint
from ddm.datadonation.serializers import DonationSerializer
from ddm.encryption.models import Decryption
from ddm.participation.models import Participant
from ddm.projects.models import DonationProject
from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from smtplib import SMTPException

from ..tool.models import Classroom


class BaseReport:
    """
    Base class for all reports. Assumes that class.url_id is passed
    as 'url_id' in the URL.
    """

    def setup(self, request, *args, **kwargs):
        """Add classroom and project objects to the object."""
        super().setup(request, *args, **kwargs)
        self.register_classroom()
        self.register_project()

    def dispatch(self, request, *args, **kwargs):
        if not self.classroom.is_active:
            redirect_url = reverse_lazy(
                'class_expired', kwargs={'url_id': self.classroom.url_id})
            return redirect(redirect_url)
        return super().dispatch(request, *args, **kwargs)

    def get_class_id(self):
        """Get the class ID from the URL."""
        return self.kwargs.get('url_id')

    def register_classroom(self):
        """Register classroom object."""
        self.classroom = Classroom.objects.get(url_id=self.get_class_id())

    def register_project(self):
        """Register project object."""
        project_id = self.classroom.base_module.ddm_project_id
        self.project = DonationProject.objects.get(url_id=project_id)


class BaseReportClassroom(BaseReport, ListView):
    model = Participant

    def get_queryset(self):
        return Participant.objects.filter(
            project__url_id=self.project.url_id,
            extra_data__url_param__class=self.classroom.url_id
        )

    def get_donations(self):
        """Get the donations for the report."""
        blueprints = DonationBlueprint.objects.filter(project=self.project)
        decryptor = Decryption(self.project.secret, self.project.get_salt())

        donations = {}
        for blueprint in blueprints:
            blueprint_donations = blueprint.datadonation_set.filter(
                participant__in=self.object_list, status='success')

            if len(blueprint_donations) >= 5:
                donations[blueprint.name] = DonationSerializer(
                    blueprint_donations, many=True, decryptor=decryptor).data
            else:
                donations[blueprint.name] = None
        return donations

    def get_responses(self):
        """Get the responses for the report."""
        # TODO: Implement this once the questionnaire is implemented.
        pass

    def get_data(self):
        """Get the data for the report."""
        return {
            'donations': self.get_donations(),
            'responses': self.get_responses()
        }


class BaseReportIndividual(BaseReport, DetailView):
    model = Participant
    lookup_field = 'external_id'
    slug_field = 'external_id'
    slug_url_kwarg = 'participant_id'

    def get_donations(self):
        """
        Get the participant's donations from the database.

        Returns a dictionary with the blueprint name as the key and the
        corresponding donation data as the value.
        """
        blueprints = DonationBlueprint.objects.filter(project=self.project)
        decryptor = Decryption(self.project.secret, self.project.get_salt())

        donations = {}
        for blueprint in blueprints:
            blueprint_donation = blueprint.datadonation_set.filter(
                participant=self.object, status='success').first()
            if blueprint_donation:
                donations[blueprint.name] = DonationSerializer(
                    blueprint_donation, decryptor=decryptor).data
        return donations

    def get_responses(self):
        """
        Get the participant's responses from the database.
        """
        # TODO: Implement this once the questionnaire is implemented.
        return {}

    def get_data(self):
        """Get the participant's data from the database."""
        data = {
            'donations': self.get_donations(),
            'responses': self.get_responses()
        }
        return data


class SendReportLink(View):
    """Sends the link to the open report to a given e-mail address."""

    def post(self, request, *args, **kwargs):
        post_data = json.loads(request.body)
        email_address = post_data.get('email', None)
        report_link = post_data.get('link', None)
        if email_address and report_link:
            try:
                send_mail(
                    subject='Link zum Digital Meal Report',
                    message=f'Link zum Report: {report_link}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email_address],
                    fail_silently=False
                )
                return JsonResponse({'status': 'success'})
            except SMTPException:
                return JsonResponse({'status': 'error'}, status=400)

        else:
            return JsonResponse({'status': 'error'}, status=400)

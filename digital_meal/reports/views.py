import json
from datetime import timedelta, datetime

from ddm.datadonation.models import DonationBlueprint
from ddm.datadonation.serializers import DonationSerializer
from ddm.encryption.models import Decryption
from ddm.participation.models import Participant
from ddm.projects.models import DonationProject
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.http import JsonResponse, Http404, HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from django.template.loader import render_to_string
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
        if not self.check_classroom_active():
            redirect_url = reverse_lazy(
                'class_expired', kwargs={'url_id': self.classroom.url_id})
            return redirect(redirect_url)
        return super().dispatch(request, *args, **kwargs)

    def check_classroom_active(self):
        if not self.classroom.is_active:
            return False
        else:
            return True

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

    def dispatch(self, request, *args, **kwargs):
        """
        Checks that the client requesting the report is the owner of
        the classroom for which the report is requested (or a superuser).
        """
        if not request.user.is_authenticated:
            redirect_url = reverse_lazy('account_login')
            return redirect(redirect_url + f'?next={request.path}')

        if request.user != self.classroom.owner and not request.user.is_superuser:
            raise PermissionDenied("Sie haben keinen Zugriff auf diese Klasse.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['class_name'] = self.classroom.name
        context['class_id'] = self.classroom.url_id
        context['expiration_date'] = self.classroom.expiry_date
        return context

    def get_queryset(self):
        return Participant.objects.filter(
            project__url_id=self.project.url_id,
            extra_data__url_param__class=self.classroom.url_id
        )

    def get_donations(self) -> dict:
        """
        Get the donations for the report.

        Returns:
            dict: A dictionary holding <blueprint.name>: [list of blueprint
            <donation.data>] pairs.
        """
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

    def get_responses(self) -> dict:
        """
        Get the participant's responses from the database.

        Still needs to be implemented.

        Returns:
            dict: Returns an empty dictionary until implemented.
        """
        return {}


class BaseReportIndividual(BaseReport, DetailView):
    model = Participant
    lookup_field = 'external_id'
    slug_field = 'external_id'
    slug_url_kwarg = 'participant_id'

    def get_object(self, queryset=None):
        participant = Participant.objects.filter(
            external_id=self.kwargs.get('participant_id')
        ).first()
        if not participant:
            raise Http404

        participant_url_param = participant.extra_data.get('url_param')
        if not participant_url_param:
            raise Http404

        participant_class_id = participant_url_param.get('class')
        if participant_class_id != self.classroom.url_id:
            raise Http404

        return participant

    def get_context_data(self, **kwargs):
        """
        Check if participation was longer ago then the expiration date
        (calculated using the DAYS_TO_DONATION_DELETION setting).

        If it was longer ago, render the report_expired view.
        If not, add expiration_date to context.
        """
        start_date = self.object.start_time.date()
        expiration_date = timezone.now() - timedelta(days=settings.DAYS_TO_DONATION_DELETION - 1)

        if expiration_date.date() > start_date:
            redirect_url = reverse_lazy('report_expired')
            return redirect(redirect_url)

        context = super().get_context_data(**kwargs)
        self.add_meta_info_to_context(context, expiration_date)
        return context

    def add_meta_info_to_context(
            self,
            context: dict,
            expiration_date: datetime | None = None
    ) -> dict:
        """
        Adds the following meta information to the context:
        - 'participation_date'
        - 'expiration_date'
        - 'class_id'
        - 'class_name'

        Args:
            context (dict):  The template context.
            expiration_date (datetime.datetime): The date until which the report
                is available.

        Returns:
            dict: The updated context.
        """
        context['participation_date'] = self.object.end_time.date()
        context['expiration_date'] = expiration_date
        context['class_id'] = self.get_class_id()
        context['class_name'] = self.classroom.name
        return context

    def get_donations(self) -> dict:
        """
        Get the participant's donations from the database.

        Returns:
            dict: A dictionary with the blueprint name as the key and the
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

    def get_responses(self) -> dict:
        """
        Get the participant's responses from the database.

        Still needs to be implemented.

        Returns:
            dict: Returns an empty dictionary until implemented.
        """
        return {}


class SendReportLink(View):
    """Sends the link to the open report to a given e-mail address."""

    def post(self, request, *args, **kwargs):
        post_data = json.loads(request.body)
        email_address = post_data.get('email', None)
        report_link = post_data.get('link', None)
        if email_address and report_link:
            try:
                context = {
                    'report_link': report_link
                }
                
                text_content=render_to_string('email/reporturl.txt', context)
                html_content=render_to_string('email/reporturl.html', context)
                
                try:
                    msg = EmailMultiAlternatives(
                        subject='Digital Meal: Link zur persönlichen Auswertung',
                        body=text_content,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email_address],
                        fail_silently=False
                    )
                    
                    msg.attach_alternative(html_content, "text/html")
                    msg.send()
                
                return JsonResponse({'status': 'success'})
            except SMTPException:
                return JsonResponse({'status': 'error'}, status=400)

        else:
            return JsonResponse({'status': 'error'}, status=400)


class ReportExpired(TemplateView):
    template_name = 'reports/report_expired.html'

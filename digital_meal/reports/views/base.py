import json
import logging_utils

from datetime import timedelta
from smtplib import SMTPException
from urllib.parse import urlparse

from ddm.datadonation.models import DonationBlueprint, DataDonation
from ddm.datadonation.serializers import DonationSerializer
from ddm.encryption.models import Decryption
from ddm.participation.models import Participant
from ddm.projects.models import DonationProject
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.db.models import Prefetch, QuerySet
from django.http import JsonResponse, HttpResponseNotAllowed, Http404
from django.shortcuts import redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from digital_meal.tool.models import Classroom

logger = logging.getLogger(__name__)

REPORT_TYPES = {
    'INDIVIDUAL': 'individual',
    'CLASS': 'class',
    'EXAMPLE': 'example',
}


class Report:
    """Base class for all reports.

    - Must be called with a Classroom.url_id passed as 'url_id'.
    - Adds the Classroom to self.classroom
    - Adds the related DonationProject to self.project
    - Checks if the requested Classroom is still active. If not, returns
        'class_expired' view.
    """

    classroom: Classroom = None
    project: DonationProject = None
    report_type: str = None

    def setup(self, request, *args, **kwargs):
        """Add classroom and project objects to the object."""
        super().setup(request, *args, **kwargs)
        self.register_classroom()
        self.register_project()

    def dispatch(self, request, *args, **kwargs):
        if not self.check_classroom_active():
            redirect_url = reverse_lazy(
                'class_expired',
                kwargs={'url_id': self.classroom.url_id}
            )
            return redirect(redirect_url)

        return super().dispatch(request, *args, **kwargs)

    def check_classroom_active(self) -> bool:
        """Helper method was added to be able to set this to True for example report."""
        return self.classroom.is_active

    def get_class_id(self) -> str | None:
        """Get the class ID from the URL."""
        return self.kwargs.get('url_id')

    def register_classroom(self):
        """Register classroom object."""
        self.classroom = get_object_or_404(Classroom, url_id=self.get_class_id())

    def register_project(self):
        """Register project object."""
        project_id = self.classroom.base_module.ddm_project_id
        self.project = DonationProject.objects.get(url_id=project_id)


class IndividualReport(Report, DetailView):
    """Base class for individual reports.

    - Must be called with a Classroom.url_id passed as 'url_id' and a
        Participant.external_id passed as 'participant_id'.
    - Checks if participant is part of the classroom. If not, returns 404.
    - Checks if report for participant is expired.
    - Adds report meta information to context.
    """

    model = Participant
    lookup_field = 'external_id'
    slug_field = 'external_id'
    slug_url_kwarg = 'participant_id'

    expiration_date = None
    report_type = REPORT_TYPES['INDIVIDUAL']

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Check expiration.
        expiration_info = self.check_expiration_date()
        if expiration_info['expired']:
            logger.info(
                'Individual report not rendered: expired report was requested'
            )
            redirect_url = reverse_lazy('report_expired')
            return redirect(redirect_url)

        self.expiration_date = expiration_info['expiration_date']

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        self.add_report_info_to_context(context)
        return context

    def add_report_info_to_context(self, context: dict) -> dict:
        """Adds report meta information to the context.

        Added information includes: 'participation_date', 'expiration_date',
        'class_id', and 'class_name'

        Args:
            context (dict):  The template context.

        Returns:
            dict: The updated context.
        """

        context.update({
            'participation_date': self.object.end_time.date(),
            'expiration_date': self.expiration_date,
            'class_id': self.get_class_id(),
            'class_name': self.classroom.name,
            'participant_id': self.object.external_id,
        })
        return context

    def get_object(self, queryset=None) -> Participant:
        participant_id = self.kwargs.get('participant_id')
        participant = Participant.objects.filter(
            external_id=participant_id
        ).first()
        if not participant:
            logger.info(
                'Individual report not rendered: requested for non-existing participant %s.',
                participant_id
            )
            raise Http404('Ungültige Teilnahme-ID in der URL')

        participant_url_param = participant.extra_data.get('url_param')
        if not participant_url_param or participant_url_param.get('class') is None:
            logger.info(
                'Individual report not rendered: report requested for '
                'participant without associated class information '
                '(no "class" field in participant.extra_data.url_param).'
            )
            raise Http404('Es konnte keine Klasseninformation für diese Teilnahme-ID gefunden werden.')

        participant_class_id = participant_url_param.get('class')
        if participant_class_id != self.classroom.url_id:
            logger.info(
                'Individual report not rendered: class id in URL did not match '
                'class associated with participant (url: %s, associated: %s).',
                self.classroom.url_id, participant_class_id
            )
            raise Http404('Die Klassen-ID und die Teilnahme-ID passen nicht zusammen.')

        return participant

    def check_expiration_date(self) -> dict:
        """Check if report is still accessible for this participant.

        Report is expired if the participation was longer ago then the
        expiration date (calculated using the DAYS_TO_DONATION_DELETION setting).

        Returns:
            dict: in the form {'expired': True/False, 'expiration_date': <date>}
        """

        start_date = self.object.start_time.date()
        expiration_date = timezone.now() - timedelta(days=settings.DAYS_TO_DONATION_DELETION - 1)

        if expiration_date.date() > start_date:
            expired = True
        else:
            expired = False

        return {'expired': expired, 'expiration_date': expiration_date}


class ExampleReport(TemplateView):

    template_name = None
    report_type = REPORT_TYPES['EXAMPLE']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.add_report_info_to_context(context)
        return context

    def add_report_info_to_context(self, context: dict) -> dict:
        """Adds report meta information to the context.

        Added information includes: 'participation_date', 'expiration_date',
        'class_id', and 'class_name'

        Args:
            context (dict):  The template context.

        Returns:
            dict: The updated context.
        """

        context.update({
            'participation_date': timezone.now().date(),
            'expiration_date': 'Dieser Beispielreport ist unbeschränkt verfügbar',
            'class_id': '1234567890',
            'class_name': 'Beispielklasse',
            'participant_id': 'example',
        })
        return context


class ClassReport(Report, ListView):
    """Base class for Class reports.

    - Must be called with a Classroom.url_id passed as 'url_id'.
    - Only renders report if user calling the report is the owner of the
        classroom or superuser.
    - Adds report meta information to context.
    """

    model = Participant
    report_type = REPORT_TYPES['CLASS']

    def dispatch(self, request, *args, **kwargs):
        """Checks that the client requesting the report is the owner of
        the classroom for which the report is requested (or a superuser).
        """
        if not request.user.is_authenticated:
            logger.info(
                'Unauthorized request: Class report requested by unauthenticated user.'
            )
            redirect_url = reverse_lazy('account_login')
            return redirect(redirect_url + f'?next={request.path}')

        if request.user != self.classroom.owner and not request.user.is_superuser:
            logger.warning(
                'Unauthorized request: Class report requested by authenticated '
                'user that is not classroom owner.'
            )
            raise PermissionDenied("Sie haben keinen Zugriff auf diese Klasse.")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.add_report_info_to_context(context)
        return context

    def add_report_info_to_context(self, context: dict) -> dict:
        """Adds report meta information to the context.

        Added information includes: 'expiration_date', 'class_id', 'class_name'

        Args:
            context (dict):  The template context.

        Returns:
            dict: The updated context.
        """
        context.update({
            'expiration_date': self.classroom.expiry_date,
            'class_id': self.classroom.url_id,
            'class_name': self.classroom.name,
        })
        return context

    def get_queryset(self):
        return Participant.objects.filter(
            project__url_id=self.project.url_id,
            extra_data__url_param__class=self.classroom.url_id
        )


class ReportHtmxMixin:
    """Overrides get() function to only allow htmx requests."""

    def get(self, request, **kwargs):
        is_htmx_request = request.headers.get('HX-Request')
        if is_htmx_request not in [True, 'true', 'True']:
            logger.warning(
                'Non-htmx request received for view based on HTMXMixin.'
            )
            return None

        return super().get(request, **kwargs)


class GetDonationsMixin:
    """Implements functions to retrieve donations.

    - Inheriting views must declare a 'blueprint_names' variable
        (a list of the blueprint names for which donations shall be retrieved).
    - Inheriting views must also inherit from ClassReport or IndividualReport
    - Adds the donation to self.donations. This will hold a dictionary with
        blueprint names as keys and a list of donations as values.

    Note: Mixin must be customized for the use with individual and class data
        (see GetDonationsIndividualMixin and GetDonationsClassMixin).
    """

    project: DonationProject = None
    blueprint_names: list[str] = []
    donations: dict = None

    def get_context_data(self, **kwargs):
        self.donations = self.add_donations()
        return super().get_context_data(**kwargs)

    def add_donations(self) -> dict:
        participants = self.get_participants_for_donation_query()
        donations = self.get_donations_from_db(participants)
        clean_donations = self.clean_donations_from_db(donations)
        return clean_donations

    def get_participants_for_donation_query(self) -> list[Participant]:
        """Get list of participants for which to retrieve the donations.

        Returns:
            list: List of Participant objects.
        """
        raise NotImplementedError

    def clean_donations_from_db(
            self,
            blueprints: QuerySet[DonationBlueprint]
    ) -> dict:
        raise NotImplementedError

    def get_donations_from_db(
            self,
            participants: list[Participant]
    ) -> QuerySet[DonationBlueprint]:
        """
        Retrieve the encrypted data donations related to the provided blueprints
        that have been donated by the provided participants.

        Args:
            participants: List of Participant instances

        Returns:
            QuerySet: A queryset of DonationBlueprints.
        """
        blueprints = DonationBlueprint.objects.filter(
            project=self.project,
            name__in=self.blueprint_names
        ).prefetch_related(
            Prefetch(
              'datadonation_set',
              queryset=DataDonation.objects.filter(
                  participant__in=participants,
                  status='success'
              )
            )
        )
        return blueprints


class GetDonationsIndividualMixin(GetDonationsMixin):
    """Extends the GetDonationsMixin for the use with individual data."""

    def get_participants_for_donation_query(self) -> list[Participant]:
        participant = self.object

        if not isinstance(participant, Participant):
            raise TypeError(
                f'Participant object expected, received {type(participant)}')

        return [participant]

    def clean_donations_from_db(
            self,
            blueprints: QuerySet[DonationBlueprint]
    ) -> None:
        """Decrypts blueprint donations and stores them in a result dict.

        Args:
            blueprints: The donation blueprints for which to retrieve donations.

        Returns:
            dict: With the blueprint names as keys, holding the respective
                decrypted donation information.
        """
        decryptor = Decryption(self.project.secret, self.project.get_salt())

        donations = {}
        for blueprint in blueprints:
            blueprint_donations = blueprint.datadonation_set.all()

            if blueprint_donations:
                donations[blueprint.name] = DonationSerializer(
                    blueprint_donations[0], decryptor=decryptor).data

        return donations


class GetDonationsClassMixin(GetDonationsMixin):
    """Extends the GetDonationsMixin for the use with class data."""

    def get_participants_for_donation_query(self) -> list[Participant]:
        participants = self.object_list

        if len(participants) == 0:
            return []

        if not isinstance(participants[0], Participant):
            raise TypeError(
                f'Participant object expected, received {type(participants[0])}'
            )

        return list(participants)

    def clean_donations_from_db(
            self,
            blueprints: QuerySet[DonationBlueprint]
    ) -> dict:
        """Decrypts blueprint donations and stores them in a result dict.

        Does not return donations if less than five participants have participated.

        Args:
            blueprints: The donation blueprints for which to retrieve donations.

        Returns:
            dict: With the blueprint names as keys, holding the respective
                decrypted donation information.
        """
        decryptor = Decryption(self.project.secret, self.project.get_salt())

        clean_donations = {}
        for blueprint in blueprints:
            blueprint_donations = blueprint.datadonation_set.all()

            min_n_donations = 5

            if len(blueprint_donations) >= min_n_donations:
                clean_donations[blueprint.name] = DonationSerializer(
                    blueprint_donations, many=True, decryptor=decryptor).data

                n_available = 0
                for donation in clean_donations[blueprint.name]:
                    if donation.get('data'):
                        n_available += 1

                if n_available < min_n_donations:
                    clean_donations[blueprint.name] = None

            else:
                clean_donations[blueprint.name] = None

        return clean_donations


class BlueprintReportMixin:
    """Base mixin to use blueprint donations for partial report.

    Provides functionality to:

    - Load donation data for a specific blueprint from self.donations
    """

    def get_blueprint_donation_data(self, blueprint_name: str):
        """Load and clean blueprint donation data."""
        bp_donation_data = self.load_blueprint_donation_data(blueprint_name)
        clean_bp_donation_data = self.clean_blueprint_donation_data(bp_donation_data)
        return clean_bp_donation_data

    def load_blueprint_donation_data(self, blueprint_name: str) -> list[list]:
        """Loads the donation data for the given blueprint.

        Args:
            blueprint_name: Blueprint for which to load the donation data.

        Returns:
            list: The list of donation data for the given blueprint.
        """
        blueprint_donation = self.donations.get(blueprint_name)

        donation_data = []
        if blueprint_donation is None:
            # e.g., because less than 5 people participated for a class report.
            return []

        elif isinstance(blueprint_donation, list):
            for donation in blueprint_donation:
                if donation.get('data') is None:
                    logger.info(
                        'Empty donation: received empty donation for blueprint %s',
                        blueprint_name
                    )
                    continue

                else:
                    donation_data.append(donation.get('data'))

        else:
            if blueprint_donation.get('data') is None:
                logger.info(
                    'Empty donation: received empty donation for blueprint %s',
                    blueprint_name
                )
            else:
                donation_data.append(blueprint_donation.get('data'))

        return donation_data

    def clean_blueprint_donation_data(self, donation_data: list[list]):
        """Cleans the donation data for the given blueprint donation data.

        Must be implemented by subclasses.
        """
        raise NotImplementedError()

    def log_error(self, fun_name, e):
        current_class = type(self).__name__
        logger.error(
            '%s [%s]: error in %s: %s',
            current_class, self.report_type, fun_name, e
        )
        return


class SendReportLink(View):
    """Sends the link to the open report to a given e-mail address."""

    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(['POST'])

    def post(self, request, *args, **kwargs):
        try:
            post_data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

        email_address = post_data.get('email', None)
        report_link = post_data.get('link', None)

        if not email_address:
            return JsonResponse({'status': 'error', 'message': 'Email required'}, status=400)

        if not self.validate_email(email_address):
            return JsonResponse({'status': 'error', 'message': 'Invalid email address'}, status=422)

        if not report_link:
            return JsonResponse({'status': 'error', 'message': 'Link required'}, status=400)

        if not self.validate_link(report_link):
            return JsonResponse({'status': 'error', 'message': 'Invalid link'}, status=403)

        context = {
            'report_link': report_link
        }

        text_content = render_to_string('email/reporturl.txt', context)
        html_content = render_to_string('email/reporturl.html', context)

        try:
            msg = EmailMultiAlternatives(
                subject='Digital Meal: Link zur persönlichen Auswertung',
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email_address]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
        except SMTPException as e:
            logger.error(f'Failed to send email to {email_address}: {e}')
            return JsonResponse({'status': 'error', 'message': 'Failed to send email'}, status=500)

        return JsonResponse({'status': 'success'})

    def validate_link(self, link: str) -> bool:
        """Check if the link follows an allowed structure.

        Link must follow the https protocol and its main domain must be listed
        in settings.ALLOWED_REPORT_DOMAINS.

        Args:
            link: The link to check.

        Returns:
            bool: True if the link is allowed, False otherwise.
        """
        allowed_scheme = ['https']
        allowed_domains = settings.ALLOWED_REPORT_DOMAINS

        parsed_link = urlparse(link)

        if parsed_link.scheme not in allowed_scheme:
            return False

        if parsed_link.netloc not in allowed_domains:
            return False

        return True

    def validate_email(self, email: str) -> bool:
        """Check if a string represents a valid email address.

        Args:
            email: The email address to check.

        Returns:
            bool: True if the email is valid, False otherwise.
        """
        try:
            validate_email(email)
            return True
        except ValidationError:
            return False


class ReportExpired(TemplateView):
    template_name = 'reports/report_expired.html'

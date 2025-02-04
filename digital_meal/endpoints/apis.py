import io
import json
import zipfile

from django.core.exceptions import PermissionDenied, BadRequest
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from ddm.models.auth import ProjectTokenAuthenticator
from ddm.models.core import (
    Participant, DonationBlueprint, DataDonation, DonationProject,
    QuestionnaireResponse
)
from ddm.models.encryption import Decryption
from ddm.models.serializers import (
    ProjectSerializer, SerializerDecryptionMixin, DonationSerializer,
    ResponseSerializer
)
from ddm.views.apis import DDMAPIMixin, user_is_allowed

from rest_framework import authentication, permissions, serializers
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.response import Response
from rest_framework.views import APIView


class DonationSerializerAlt(SerializerDecryptionMixin,
                            serializers.HyperlinkedModelSerializer):
    project = serializers.IntegerField(source='project.id')
    participant = serializers.IntegerField(source='participant.id')

    class Meta:
        model = DataDonation
        fields = [
            'time_submitted',
            'consent',
            'status',
            'project',
            'participant'
        ]


class DDMBaseProjectApi(APIView, DDMAPIMixin):

    authentication_classes = [ProjectTokenAuthenticator,
                              authentication.SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @sensitive_variables()
    def get(self, request, format=None, *args, **kwargs):
        project = self.get_project()
        self.check_request_allowed(request, project)
        secret = self.get_secret(request, project)
        data = self.get_data(project, secret)
        response = self.create_response(data)
        self.create_event_log(
            descr='Data Request Successful',
            msg='The project data was requested successfully.'
        )
        return response

    def get_project(self):
        """ Returns project instance based on request parameter. """
        return DonationProject.objects.filter(pk=self.kwargs['pk']).first()

    def check_request_allowed(self, request, project):
        if not user_is_allowed(request.user, project):
            self.create_event_log(
                descr='Forbidden Request',
                msg='Request user is not permitted to download the data.'
            )
            raise PermissionDenied
        return

    def get_data(self, project, secret):
        return {}

    def create_response(self, data, **kwargs):
        response = self.create_zip_response(data)
        return response

    def get_secret(self, request, project):
        secret = project.secret_key
        if project.super_secret:
            if 'Super-Secret' not in request.headers:
                super_secret = None
            else:
                super_secret = request.headers['Super-Secret']
            if super_secret is None:
                self.create_event_log(
                    descr='Failed Attempt',
                    msg='Data requested without supplying secret.'
                )
                raise PermissionDenied
            else:
                secret = super_secret
        return secret

    def create_zip_response(self, data):
        """ Creates an HttpResponse object containing the created zip file. """
        zip_in_mem = self.create_zip(data)
        response = HttpResponse(zip_in_mem, content_type='application/zip')
        response['Content-Length'] = len(zip_in_mem)
        response['Content-Disposition'] = 'attachment; filename=zipfile.zip'
        return response

    @staticmethod
    def create_zip(content, filename='data.json'):
        """ Creates a zip file in memory. """
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode='w',
                             compression=zipfile.ZIP_DEFLATED) as zf:
            with zf.open(filename, 'w') as json_file:
                json_file.write(
                    json.dumps(
                        content,
                        ensure_ascii=False,
                        separators=(',', ':')
                    ).encode('utf-8')
                )
                zf.testzip()
        zip_in_memory = buffer.getvalue()
        buffer.flush()
        return zip_in_memory


class ClassOverviewAPI(DDMBaseProjectApi):
    """
    API endpoint to gather classroom statistics overview for a project.

    This API collects and returns the following data in a dictionary:
    - n_donations: The number of donations collected in the class for each
        blueprint,
    - n_finished: The number of participants who have completed the
        donation process,
    - n_not_finished: The number of participants who have not completed the
        donation process,
    - donation_dates: The dates when the donations collected in the class
        were uploaded.

    Expected parameters:
    - 'class': External classroom ID (required)

    Raises:
        BadRequest: If the 'class' parameter is not provided.
    """
    def create_response(self, data, **kwargs):
        response = Response(json.dumps(data))
        return response

    def get_formatted_date_list(self, date_list):
        return [d.strftime('%Y-%m-%dT%H:%M:%S.%fZ') for d in set(date_list)]

    def get_data(self, project, secret):
        classroom_id = self.request.query_params.get('class')
        if not classroom_id:
            raise BadRequest('No classroom id provided')

        participants = Participant.objects.filter(
            project=project, extra_data__url_param__class=classroom_id
        )
        participant_ids = participants.values_list('id', flat=True)
        n_started = len(participants)
        n_finished = len(participants.filter(completed=True))

        n_donations = {}
        donation_dates = []
        blueprints = DonationBlueprint.objects.filter(project=project)
        for blueprint in blueprints:
            blueprint_donations = blueprint.datadonation_set.filter(
                participant__pk__in=participant_ids,
                status='success'
            ).defer('data')

            n_donations[blueprint.name] = len(blueprint_donations)
            donation_dates.extend(
                blueprint_donations.values_list('time_submitted', flat=True))

        data = {
            'n_donations': n_donations,
            'n_finished': n_finished,
            'n_not_finished': (n_started - n_finished),
            'donation_dates': self.get_formatted_date_list(donation_dates)
        }
        return data


class ClassReportAPI(DDMBaseProjectApi):
    """
    API endpoint to gather the data required to generate a classroom report.

    The data includes the donations of all participants belonging to the
    classroom if at least 5 donations exist. Otherwise, it returns None for
    the donations.

    Expected parameters:
    - 'class': External classroom ID (required)

    Raises:
        BadRequest: If the 'class' parameter is not provided.
    """
    def create_response(self, data, **kwargs):
        response = Response(json.dumps(data))
        return response

    def get_data(self, project, secret):
        classroom_id = self.request.query_params.get('class')
        if not classroom_id:
            raise BadRequest('No classroom id provided')

        participants = Participant.objects.filter(
            project=project, extra_data__url_param__class=classroom_id
        ).values_list('id', flat=True)
        blueprints = DonationBlueprint.objects.filter(project=project)
        donations = {}

        try:
            decryptor = Decryption(secret, project.get_salt())
            for bp in blueprints:
                bp_donations = bp.datadonation_set.filter(
                    participant__pk__in=participants, status='success')
                if len(bp_donations) < 5:
                    donations[bp.name] = None
                else:
                    donations[bp.name] = [
                        DonationSerializer(d, decryptor=decryptor).data
                        for d
                        in bp_donations
                    ]
        except ValueError:
            self.create_event_log(
                descr='Failed Download Attempt',
                msg='Download requested with incorrect secret.'
            )
            raise PermissionDenied

        data = {
            'project': ProjectSerializer(project).data,
            'donations': donations,
        }
        return data


class IndividualReportAPI(DDMBaseProjectApi):
    """
    API endpoint to gather the data required to generate an individual report.

    Expected parameters:
    - 'participant_id': external participant id
    """

    def create_response(self, data, **kwargs):
        response = Response(json.dumps(data))
        return response

    def get_participant(self):
        participant_id = self.request.query_params.get('participant_id')
        return Participant.objects.filter(
            project=self.project,
            external_id=participant_id
        ).first()

    def get_data(self, project, secret):
        participant_id = self.get_participant()
        self.check_participant_allowed(participant_id)

        blueprints = DonationBlueprint.objects.filter(project=project)
        responses = QuestionnaireResponse.objects.filter(
            project=project,
            participant__external_id__in=participant_id
        ).first()

        donations = {}
        try:
            decryptor = Decryption(secret, project.get_salt())

            for bp in blueprints:
                bp_donation = bp.datadonation_set.filter(
                    participant__external_id=participant_id,
                    status='success'
                ).first()
                if bp_donation:
                    donations[bp.name] = DonationSerializer(
                        bp_donation, decryptor=decryptor).data

            if responses:
                responses = [
                    ResponseSerializer(
                        r, decryptor=decryptor).data['responses']
                    for r in responses
                ]

        except ValueError:
            self.create_event_log(
                descr='Failed request',
                msg='Request with incorrect secret.'
            )
            raise PermissionDenied

        data = {
            'project': ProjectSerializer(project).data,
            'donations': donations,
            'responses': responses
        }
        return data

    @staticmethod
    def check_participant_allowed(participant):
        if not participant:
            raise ParseError

        if not participant.completed:
            raise NotFound

        if not (
            participant.end_time + timezone.timedelta(days=90)
        ) > timezone.now():
            raise PermissionDenied

        return True

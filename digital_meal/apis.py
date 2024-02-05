import io
import json
import zipfile

from django.core.exceptions import PermissionDenied, BadRequest
from django.http import HttpResponse
from django.views.decorators.debug import sensitive_variables

from ddm.models.auth import ProjectTokenAuthenticator
from ddm.models.core import (
    Participant, DonationBlueprint, DataDonation, DonationProject
)
from ddm.models.encryption import Decryption
from ddm.models.serializers import (
    ProjectSerializer, ParticipantSerializer, SerializerDecryptionMixin
)
from ddm.views.apis import DDMAPIMixin, user_is_allowed

from rest_framework import authentication, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView


class DonationSerializerAlt(SerializerDecryptionMixin, serializers.HyperlinkedModelSerializer):
    project = serializers.IntegerField(source='project.id')
    participant = serializers.IntegerField(source='participant.id')

    class Meta:
        model = DataDonation
        fields = ['time_submitted', 'consent', 'status', 'project', 'participant']


class DDMApiBase(APIView, DDMAPIMixin):
    """
    Download all data collected for a given donation project.

    Returns:
    - GET: A Response object with the complete data associated to a project (i.e.,
    donated data, questionnaire responses, metadata) and status code.

    Example Usage:
    ```
    GET /api/project/<project_pk>/data

    Returns a ZIP-Folder containing a json file with the following structure:
    {
        'project': {<project information>},
        'donations': {<collected donations per file blueprint>},
        'participants': {<participant information>}
    }
    ```

    Authentication Methods:
    - Token authentication for remote calls.
    - Session authentication for access through web application (by verifying
        that the requesting user is the project owner).

    Error Responses:
    - 400 Bad Request: If there's an issue with the input data.
    - 401 Unauthorized: If authentication fails.
    - 403 Forbidden: If a user is not permitted to access a project (session
        authentication only).
    """
    authentication_classes = [ProjectTokenAuthenticator,
                              authentication.SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @sensitive_variables()
    def get(self, request, format=None, *args, **kwargs):
        """
        Return a zip container that contains a json file which holds the
        data donations and questionnaire responses.
        """
        project = self.get_project()
        self.check_user_allowed(request, project)
        secret = self.get_secret(request, project)
        data = self.get_data(project, secret)
        response = self.create_response(data)
        self.create_event_log(
            descr='Data Download Successful',
            msg='The project data was downloaded.'
        )
        return response

    def extract_query_parameters(self, **kwargs):
        pass

    def check_user_allowed(self, request, project):
        if not user_is_allowed(request.user, project):
            self.create_event_log(
                descr='Forbidden Download Request',
                msg='Request user is not permitted to download the data.'
            )
            raise PermissionDenied
        return

    def get_data(self, project, secret, **kwargs):
        # Gather project data in dictionary.
        blueprints = DonationBlueprint.objects.filter(project=project)
        participants = Participant.objects.filter(project=project)
        try:
            decryptor = Decryption(secret, project.get_salt())

            donations = {}
            for blueprint in blueprints:
                blueprint_donations = blueprint.datadonation_set.all().defer('data')
                donations[blueprint.name] = [DonationSerializerAlt(d, decryptor=decryptor).data for d in
                                             blueprint_donations]

            data = {
                'project': ProjectSerializer(project).data,
                'donations': donations,
                'participants': [ParticipantSerializer(p).data for p in participants]
            }
        except ValueError:
            self.create_event_log(
                descr='Failed Download Attempt',
                msg='Download requested with incorrect secret.'
            )
            raise PermissionDenied
        return data

    def create_response(self, data, **kwargs):
        zip_in_mem = self.create_zip(data)
        response = self.create_zip_response(zip_in_mem)
        return response

    def get_secret(self, request, project):
        secret = project.secret_key
        if project.super_secret:
            super_secret = None if 'Super-Secret' not in request.headers else request.headers['Super-Secret']
            if super_secret is None:
                self.create_event_log(
                    descr='Failed Download Attempt',
                    msg='Download requested without supplying secret.'
                )
                raise PermissionDenied
            else:
                secret = super_secret
        return secret

    @staticmethod
    def create_zip(content):
        """ Creates a zip file in memory. """
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            with zf.open('data.json', 'w') as json_file:
                json_file.write(json.dumps(content, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
                zf.testzip()
        zip_in_memory = buffer.getvalue()
        buffer.flush()
        return zip_in_memory

    @staticmethod
    def create_zip_response(zip_file):
        """ Creates an HttpResponse object containing the provided zip file. """
        response = HttpResponse(zip_file, content_type='application/zip')
        response['Content-Length'] = len(zip_file)
        response['Content-Disposition'] = 'attachment; filename=zipfile.zip'
        return response


class ClassReportAPI(DDMApiBase):
    """ Class to gather data for Classroom report. """

    classroom_id = None

    def get_project(self):
        """ Returns project instance. """
        return DonationProject.objects.filter(pk=self.kwargs['pk']).first()

    def extract_query_parameters(self, **kwargs):
        super().extract_query_parameters(**kwargs)
        print(f'params: {self.request.query_params}')
        self.classroom_id = self.request.query_params.get('dmclsrm')
        return

    def get_data(self, project, secret):
        # blueprints = DonationBlueprint.objects.filter(project=project)
        self.extract_query_parameters()
        if not self.classroom_id:
            raise BadRequest('No classroom id provided')

        participants = Participant.objects.filter(
            project=project,
            extra_data__url_param__dmclsrm=self.classroom_id
        )

        data = {
            'participants': [ParticipantSerializer(p).data for p in participants]
        }
        return data

    def create_response(self, data, **kwargs):
        response = Response(data)
        return response


class ClassOverviewAPI(DDMApiBase):
    """ Class to gather data for Classroom overview. """

    classroom_id = None

    def extract_query_parameters(self, **kwargs):
        super().extract_query_parameters(**kwargs)
        self.classroom_id = self.request.query_params.get('dmclsrm')
        return


def get_participant_overview():
    """ Get participant overview for classroom. """
    pass


def get_participant_data():
    """ Get participant data for classroom """
    pass

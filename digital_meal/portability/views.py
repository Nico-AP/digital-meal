import logging
import requests

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from digital_meal.portability.models import OAuthToken, TikTokAccessToken


logger = logging.getLogger(__name__)


def render_http_400(request, e: str) -> HttpResponse:
    """
    Returns a http 400 response using a custom template.

    Args:
        request: A request object.
        e (str): The error message to display to users.

    Returns:
        HttpResponse: A http response with status code 400.
    """
    context = {'error_message': e}
    return render(
        request, 'portability/400.html', context, status=400)


class StateTokenMixin:
    """
    Adds utility function to a view to be able to generate, store, and retrieve
    state tokens (e.g., to prevent csrf attacks when authenticating with
    external services without exposing the actual csrf token).
    """

    def store_state_token_in_session(
            self,
            state_token: str,
            session_key: str = 'state_token'
    ):
        """
        Stores a state token in the current user's session under the provided
        session key.

        Args:
            state_token (str): The state token to be stored.
            session_key (str): The key used to store the token in the session.

        Returns:
            None
        """
        self.request.session[session_key] = state_token
        return

    def get_or_create_state_token(
            self,
            session_key: str = 'state_token'
    ) -> str | None:
        """
        Get the state token from the current user's session. If no token exists,
        create a new OAuthToken object and return its token.

        If a session is already assigned a token and the token is still valid,
        return the existing token.

        Args:
            session_key (str): The key used to store the token in the session
                (optional).

        Returns:
            str | None: The retrieved state token if it is found in the session,
                None otherwise.
        """
        # Check if session already has an associated token
        session_token = self.request.session.get(session_key)
        if session_token:
            token = OAuthToken.objects.filter(token=session_token).first()
            if token and not token.is_expired() and not token.used:
                return token.token

        # If session has no associated (valid) token
        token = OAuthToken.objects.create()
        return token.token

    def verify_and_consume_state_token(
            self,
            state_token: str,
            session_key: str = 'state_token'
    ) -> True:
        """
        Verifies if a given state_token is the same as the one stored in the
        current session. If the token exists, the token will be deleted from the
        session and the corresponding OAuthToken model will be set to used.

        Returns True, if the token is valid. Otherwise, the function will
        raise a ValidationError.

        Args:
            state_token (str): The state token to be verified.
            session_key (str): The key used to store the token in the session
                (optional).

        Returns:
            bool: True
        """
        session_token = self.request.session.get(session_key)
        if not session_token == state_token:
            msg = 'Received state token does not match the session state token.'
            logger.info(msg)
            raise ValidationError(msg)

        if not OAuthToken.objects.filter(token=session_token).exists():
            logger.info('Tried to retrieve OAuthToken (state token) that does not exist.')
            raise ValidationError('Authentication token does not exist.')

        token = OAuthToken.objects.get(token=session_token)
        if token.is_expired() or token.used:
            logger.info('Tried to use expired OAuthToken (state token).')
            raise ValidationError('Authentication token is expired.')

        # If token is valid, set it to used and delete token from session.
        token.used = True
        token.save()
        self.request.session[session_key] = None
        return True


class AccessTokenMixin:

    @staticmethod
    def get_valid_access_token_from_db(token_pk: int) -> str:
        """
        Tries to get the TikTokAccessToken related to the given primary key.
        If a token object is found, validates whether the token has expired and
        if it has, tries to refresh the token.

        If the token exists and is valid, the access token is returned.
        Otherwise, an exception is raised.

        Returns:
            str: The token if it exists and is valid.

        Raises:
            TikTokAccessToken.DoesNotExist: If the TikTokAccessToken does not exist.
            ValidationError: If the token cannot be found or is invalid.
        """
        # Check if related access token exists in db.
        access_token = TikTokAccessToken.objects.filter(pk=token_pk).first()
        if not access_token:
            logger.info('Tried to retrieve inexistent TikTokAccessToken.')
            raise TikTokAccessToken.DoesNotExist(
                f'No TikTokAccessToken found for '
                f'provided primary key "{token_pk}".'
            )

        # Check if the access token is expired.
        if access_token.is_expired():
            # Try to refresh token.
            access_token = access_token.refresh()
            if not access_token:
                raise ValidationError(
                    f'TikTokAccessToken is expired and cannot be refreshed '
                    f'(pk: {token_pk}).'
                )

        return access_token.token

    def store_access_token_pk_in_session(
            self,
            token_pk: int,
            session_id: str = 'tiktok_access_token_pk'
    ) -> None:
        """
        Stores the primary key of the related TikTokAccessToken object in the
        session.

        Args:
            token_pk (int): Primary key of the token object.
            session_id (str): The key under which the token pk is stored in the
                session (optional; defaults to 'tiktok_access_token_pk').

        Returns:
            None
        """
        self.request.session[session_id] = token_pk
        return

    def get_access_token_pk_from_session(
            self,
            session_id: str = 'tiktok_access_token_pk'
    ) -> int | None:
        """
        Gets the primary key of the related TikTokAccessToken object from the
        session.

        Args:
            session_id (str): The key under which the token pk is stored in the
                session (optional; defaults to 'tiktok_access_token_pk').

        Returns:
            int | None: Primary key of the token object. None, if session_id did
                not exist in the session.
        """
        return self.request.session.get(session_id)


class TikTokAuthView(StateTokenMixin, TemplateView):
    template_name = 'portability/tiktok_auth.html'
    state_token = None

    def dispatch(self, request, *args, **kwargs):
        # Get state token used for csrf checks.
        self.state_token = self.get_or_create_state_token()
        self.store_state_token_in_session(self.state_token)
        return super().dispatch(request, *args, **kwargs)

    def build_auth_url(self) -> str:
        """
        Builds the TikTok authentication URL to be included in the template.

        Returns:
            str: The TikTok authentication URL.
        """
        auth_url = settings.TIKTOK_AUTH_URL
        client_key = settings.TIKTOK_CLIENT_KEY
        scope = 'user.info.basic'
        redirect_uri = settings.TIKTOK_REDIRECT_URL
        state = self.state_token
        response_type = 'code'

        return (
            auth_url +
            '?client_key=' + client_key +
            '&scope=' + scope +
            '&redirect_uri=' + redirect_uri +
            '&state=' + state +
            '&response_type=' + response_type
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tt_auth_url'] = self.build_auth_url()
        return context


class TikTokCallbackView(AccessTokenMixin, StateTokenMixin, View):
    """
    Handles the callback from TikTok after authentication. Validates the
    received data and retrieves the access token from TikTok.

    If the validation and token retrieval was successful, the user is redirected
    to the TikTokDataReviewView.

    If the validation fails, the user is redirected to an error page.
    """
    def dispatch(self, request, *args, **kwargs):
        # Validate state token before any processing
        state = request.GET.get('state')
        if not state:
            logger.info('Request is missing state token.')
            # TODO: Render better templates.
            return render_http_400(request, 'Missing state parameter')

        try:
            self.verify_and_consume_state_token(state)
        except ValidationError as e:
            return render_http_400(request, f'Authentication failed: {e}')

        # Check for errors raised by the external service.
        error = request.GET.get('error')
        if error:
            descr = request.GET.get('error_description')
            logger.error(f'Authentication with TikTok failed due '
                         f'to the following error: {error} ({descr}')
            return render_http_400(
                request, f'Authentication failed: {descr} ({error})')

        # Check for authorization code
        if not request.GET.get('code'):
            logger.info('Request is missing "code" parameter.')
            return render_http_400(request, 'Missing authorization code')

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Get access token information from TikTok.
        token_data = self.exchange_code_for_token()

        if not token_data:
            return render_http_400(
                request,'Access token could not be retrieved from TikTok.')

        if not self.check_token_data_is_valid(token_data):
            try:
                token_info = token_data.keys()
            except AttributeError:
                token_info = token_data
            logger.error(f'Received invalid token data from TikTok: {token_info}')

        # Check if token for user already exists and if yes, delete existing one.
        user_id = token_data.get('open_id')
        existing_token = TikTokAccessToken.objects.filter(open_id=user_id).first()

        if existing_token is not None:
            existing_token.delete()

        # Create token object in db if needed.
        token = self.create_access_token_in_db(token_data)

        # Save link to token object in session.
        self.store_access_token_pk_in_session(token.pk)

        # Redirect to data review view.
        return redirect('tiktok_data_review')

    @staticmethod
    def check_token_data_is_valid(token_data: dict) -> bool:
        """
        Check if the received token data is a dictionary and contains the
        expected fields.

        Args:
            token_data (dict): The received token data.

        Returns:
            bool: True if data is valid, False otherwise.
        """
        if not isinstance(token_data, dict):
            return False

        expected_fields = [
            'access_token',
            'expires_in',
            'open_id',
            'refresh_expires_in',
            'refresh_token',
            'scope',
            'token_type'
        ]
        return all(k in token_data for k in expected_fields)

    @staticmethod
    def create_access_token_in_db(token_data: dict) -> TikTokAccessToken:
        """
        Creates a new access token in the database based on the data received
        from TikTok's API.

        Args:
            token_data (dict): Dictionary holding the Token information.

        Returns:
            TikTokAccessToken: The newly created TikTokAccessToken object.
        """
        token_expiration_date = timezone.now() + timedelta(seconds=token_data['expires_in'])
        refresh_token_expiration_date = timezone.now() + timedelta(seconds=token_data['refresh_expires_in'])

        token = TikTokAccessToken.objects.create(
            token=token_data['access_token'],
            token_expiration_date=token_expiration_date,
            refresh_token=token_data['refresh_token'],
            refresh_token_expiration_date=refresh_token_expiration_date,
            open_id=token_data['open_id'],
            scope=token_data['scope'],
            token_type=token_data['token_type'],
        )
        return token

    def exchange_code_for_token(self) -> dict | None:
        """
        Loads the authorization code received from TikTok from the request
        object and requests the corresponding access token from the TikTok User
        Management API endpoint.

        Returns:
            dict | None: The JSON response from the TikTok API endpoint.
                None, if request failed.
        """
        url = settings.TIKTOK_TOKEN_URL
        data = {
            'client_key': settings.TIKTOK_CLIENT_KEY,
            'client_secret': settings.TIKTOK_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'redirect_uri': settings.TIKTOK_REDIRECT_URL,
            'code': self.request.GET.get('code')
        }
        headers = {'Accept': 'application/json'}

        try:
            response = requests.post(url, data=data, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to retrieve authentication token: {e}')
            return None


class TikTokDataReviewView(AccessTokenMixin, TemplateView):
    """
    Gets user information from the TikTok User Info API.

    """
    template_name = 'portability/tiktok_data_review.html'
    access_token = None

    def dispatch(self, request, *args, **kwargs):
        # Check if access token is available and valid.
        token_pk = self.get_access_token_pk_from_session()
        if not token_pk:
            msg = 'Access token information missing in session.'
            logger.warning(msg)
            return render_http_400(request, msg)

        try:
            access_token = self.get_valid_access_token_from_db(token_pk)
        except (TikTokAccessToken.DoesNotExist, ValidationError) as e:
            logger.error(f'Failed to get access token: {e}')
            return render_http_400(
                request, 'The linked access token does not exist or is invalid.')

        self.token = access_token
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_info_retrieved = False

        response = self.get_user_info_from_tiktok()
        if response:
            user_data = response.get('data')
            if user_data:
                user_info = user_data.get('user')
                user_info.pop('union_id', None)
                user_info = self.prettify_user_info(user_info)
                user_info_retrieved = True
            else:
                logger.warning('Response from TikTok User Info API is missing "data" key.')
                user_info = None

            context['user_info'] = user_info

        context['user_info_retrieved'] = user_info_retrieved
        return context

    @staticmethod
    def prettify_user_info(user_info: dict) -> dict:
        """
        Takes a user info dictionary and prettifies its labels by removing
        underscores and capitalizing the words.

        Args:
            user_info (dict): A dictionary.

        Returns:
            dict: The dictionary with prettified labels.
        """
        pretty_dict = {}
        user_info = {'display_name': user_info.pop('display_name'), **user_info}

        for label, value in user_info.items():
            label = label.replace('_', ' ').title()
            pretty_dict[label] = value

        return pretty_dict

    def get_user_info_from_tiktok(self) -> dict | None:
        """
        Retrieves the user information from the TikTok User Info API.

        Returns:
            dict | None: The JSON response from the TikTok API endpoint.
                None, if request failed.
        """
        url = settings.TIKTOK_USER_INFO_URL
        fields = [
            'union_id',
            'display_name'
        ]
        params = {'fields': ','.join(fields)}
        headers = {'Authorization': f'Bearer {self.token}'}

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            # TODO: Handle specific errors.
            # Possible errors: {"error":{"code":"scope_not_authorized","message":"The user did not author
            # ize the scope required for completing this request.","log_id":"20250625133420FE910721C437
            # F9AB7B4D"}

            msg = f'Failed to retrieve user info: {e}'
            logger.error(msg)
            return None

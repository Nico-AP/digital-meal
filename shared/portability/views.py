import logging
import time

import requests
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.handlers.wsgi import WSGIRequest
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from digital_meal.core.logging_utils import log_security_event
from shared.portability.constants import PortabilityContexts
from shared.portability.exceptions import TokenRefreshError
from shared.portability.models import (
    OAuthStateToken,
    TikTokAccessToken,
    TikTokDataRequest,
)
from shared.portability.services import (
    TikTokAccessTokenService,
    TikTokPortabilityAPIClient,
)
from shared.portability.sessions import (
    PortabilitySessionManager,
    PortabilitySessionMixin,
)
from shared.portability.utils import get_request_context

logger = logging.getLogger(__name__)


def render_http_400(request, e: str) -> HttpResponse:
    """Returns an http 400 response using a custom template.

    Args:
        request: A request object.
        e: The error message to display to users.

    Returns:
        HttpResponse: A http response with status code 400.
    """
    context = {"error_message": e}
    return render(request, "portability/400.html", context, status=400)


def redirect_to_auth_view(
    request: WSGIRequest, msg: str = None
) -> HttpResponseRedirect:
    if msg is None:
        msg = "Something went wrong. Please try again."

    messages.info(request, msg)

    port_session = PortabilitySessionManager.from_request(request)
    port_context = port_session.get_context()

    if port_context == PortabilityContexts.MY_DM:
        return redirect("userflow:datadonation:port_tt_connect")
    else:
        return redirect("tiktok_auth")


class ManageAccessTokenMixin:
    access_token = None

    @staticmethod
    def get_valid_access_token_from_db(open_id: str) -> TikTokAccessToken:
        """Retrieves a valid access token.

        Tries to get the TikTokAccessToken related to the given primary key from
        the database. If a token object exists, validates whether the token
        has expired and if it has, refreshes the token.

        If the token exists and is valid, the TikTokAccessToken object is returned.
        Otherwise, an exception is raised.

        Args:
            open_id: The open ID of the user for which to retrieve the token.

        Returns:
            TikTokAccessToken: The token if it exists and is valid.

        Raises:
            TikTokAccessToken.DoesNotExist: If the TikTokAccessToken does not exist.
            ValidationError: If the token cannot be found or is invalid.
        """
        # Check if related access token exists in db.
        access_token = TikTokAccessToken.objects.filter(open_id=open_id).first()
        if not access_token:
            logger.info("Tried to retrieve inexistent TikTokAccessToken.")
            raise TikTokAccessToken.DoesNotExist(
                f'No TikTokAccessToken found for provided open_id "{open_id}".'
            )

        # Check if the access token is expired.
        if access_token.is_expired():
            refresh_service = TikTokAccessTokenService()

            # Try to refresh token.
            try:
                access_token = refresh_service.refresh_token(access_token)
            except TokenRefreshError as e:
                msg = (
                    "TikTokAccessToken is expired and cannot be refreshed "
                    f"(open_id: {open_id})."
                )
                raise ValidationError(msg) from e

        return access_token


class AuthenticationRequiredMixin(ManageAccessTokenMixin):
    """Ensure that the user is authenticated (open_id is in session).

    Note: Requires PortabilitySessionMixin to be listed after this mixin.
    """

    port_session: PortabilitySessionManager | None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not any(issubclass(base, PortabilitySessionMixin) for base in cls.__mro__):
            msg = f"{cls.__name__} requires PortabilitySessionMixin to be loaded after."
            raise TypeError(msg)

    def session_dispatch(self, request, *args, **kwargs) -> HttpResponse | None:
        """Redirects unauthenticated requests (open_id not in session)."""
        open_id = self.port_session.get_tiktok_open_id()
        if not open_id:
            msg = "Open ID information missing in session (unauthenticated request)."
            log_security_event(logger, msg, self.request)
            return redirect_to_auth_view(request)

        return super().session_dispatch(request, *args, **kwargs)


class ActiveAccessTokenRequiredMixin(ManageAccessTokenMixin):
    """Ensure that current session has an active access token.

    Note: Requires PortabilitySessionMixin to be loaded after
    """

    port_session: PortabilitySessionManager | None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not any(issubclass(base, PortabilitySessionMixin) for base in cls.__mro__):
            msg = f"{cls.__name__} requires PortabilitySessionMixin to be loaded after."
            raise TypeError(msg)

    def session_dispatch(self, request, *args, **kwargs) -> HttpResponse | None:
        """Redirects to auth view if session has no active access token."""
        open_id = self.port_session.get_tiktok_open_id()
        try:
            access_token = self.get_valid_access_token_from_db(open_id)
        except (TikTokAccessToken.DoesNotExist, ValidationError) as e:
            logger.error("Failed to get access token: %s", e)
            return redirect_to_auth_view(request)

        self.access_token = access_token
        self.access_token.refresh_from_db()
        return super().session_dispatch(request, *args, **kwargs)


class TikTokAuthView(PortabilitySessionMixin, TemplateView):
    template_name = "portability/tiktok_auth.html"
    state_token: str | None = None

    # TODO: Add throttling.

    def session_dispatch(self, request, *args, **kwargs) -> HttpResponse | None:
        """Generates and stores a state token used in the authentication flow."""

        state_token = self.get_or_create_state_token(request)
        self.state_token = state_token.token
        self.port_session.update(
            state_token=state_token.token,
            context=state_token.context,
        )
        return super().session_dispatch(request, *args, **kwargs)

    def get_or_create_state_token(self, request) -> OAuthStateToken:
        """Get the state token from the current user's session.

        If no token exists, create a new OAuthStateToken object and return its token.
        If a session is already assigned a token and the token is still valid,
        return the existing token.

        Returns:
            OAuthStateToken: The state token associated with this session.
        """

        session_token = self.port_session.get_token()
        context = get_request_context(request)

        # Option A: Session has no associated token
        if not session_token:
            return OAuthStateToken.objects.create(context=context)

        # Option B: Session has associated token
        token = OAuthStateToken.objects.filter(token=session_token).first()
        if token and (token.is_expired() or token.used):
            return OAuthStateToken.objects.create(context=context)

        # Option B-1: Token was created in current context
        if token.context == context:
            return token

        # Option B-2: Token was created in different context
        token.delete()
        return OAuthStateToken.objects.create(context=context)

    def build_auth_url(self) -> str:
        """Builds the TikTok authentication URL.

        Returns:
            str: The TikTok authentication URL.
        """
        auth_url = settings.TIKTOK_AUTH_URL
        client_key = settings.TIKTOK_CLIENT_KEY
        scope = "user.info.basic,portability.all.single"
        redirect_uri = settings.TIKTOK_REDIRECT_URL
        state = self.state_token
        response_type = "code"

        return (
            auth_url
            + "?client_key="
            + client_key
            + "&scope="
            + scope
            + "&redirect_uri="
            + redirect_uri
            + "&state="
            + state
            + "&response_type="
            + response_type
        )

    def get_context_data(self, **kwargs):
        """Adds the TikTok authentication URL to the template context."""
        context = super().get_context_data(**kwargs)
        context["tt_auth_url"] = self.build_auth_url()
        return context


class TikTokCallbackView(ManageAccessTokenMixin, PortabilitySessionMixin, View):
    """Handles the callback from TikTok after authentication.

    Validates the received data and retrieves the access token from TikTok.
    If the validation and token retrieval was successful, the user is redirected
    to the TikTokDataReviewView.

    If the validation fails, the user is redirected to an error page.
    """

    def session_dispatch(self, request, *args, **kwargs) -> HttpResponse | None:
        """Validates the OAuth callback before processing the request.

        Performs security checks including:
        - State token validation (CSRF protection)
        - Error parameter checking from TikTok
        - Authorization code presence validation

        Args:
            request: The HTTP request object containing callback parameters.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse | None: An HttpResponse if validation fails,
                or calls super() to continue the chain.
        """

        # Validate state token before any processing
        state = request.GET.get("state")
        if not state:
            logger.info("Request is missing state token.")
            return redirect_to_auth_view(request)

        try:
            self.verify_and_consume_state_token(state)
        except ValidationError:
            return redirect_to_auth_view(request)

        # Check for errors raised by the external service
        error = request.GET.get("error")
        if error:
            descr = request.GET.get("error_description")
            logger.error("Authentication with TikTok failed: %s (%s)", error, descr)
            return redirect_to_auth_view(request)

        # Check for authorization code
        if not request.GET.get("code"):
            logger.info('Request is missing "code" parameter.')
            return redirect_to_auth_view(request)

        return super().session_dispatch(request, *args, **kwargs)

    def verify_and_consume_state_token(self, state_token: str) -> None:
        """Verifies a given state token.

        Verifies that a state token is the same as the one stored in the
        current session. If the token exists, the token will be deleted from the
        session and the corresponding OAuthStateToken model will be set to "used".

        Args:
            state_token: The state token to be verified.

        Returns:
            None or raises a ValidationError if the token is invalid.
        """
        session_token = self.port_session.get_token()
        if session_token != state_token:
            log_security_event(
                logger,
                "Received state token does not match session state token",
                self.request,
                extra={
                    "state_token": state_token,
                    "session_token": session_token,
                },
            )
            raise ValidationError("State token does not match the session state token.")

        if not OAuthStateToken.objects.filter(token=session_token).exists():
            logger.info(
                "Tried to retrieve non existing OAuthStateToken: %s", session_token
            )
            raise ValidationError("Authentication token does not exist.")

        token = OAuthStateToken.objects.get(token=session_token)
        if token.is_expired() or token.used:
            logger.info(
                "Tried to use expired OAuthStateToken: %s (pk: %s)",
                token.token,
                token.pk,
            )
            raise ValidationError("Authentication token is expired.")

        # If token is valid, set it to used and delete token from session.
        token.used = True
        token.save()
        self.port_session.delete_token()

    def get(self, request, *args, **kwargs):
        """Exchanges the authorization code for an access token and stores it.

        Flow:
        1. Exchange authorization code for access token via TikTok API
        2. Validate the received token data structure
        3. Delete any existing tokens for this user (by open_id)
        4. Create new TikTokAccessToken in database
        5. Store token reference in session
        6. Redirect to data download awaiting page

        Args:
            request: The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: Either an error response if token exchange fails,
                or redirect to the data review view on success.
        """
        token_service = TikTokAccessTokenService()

        # Get access token information from TikTok.
        try:
            auth_code = self.request.GET.get("code")
            token_data = token_service.exchange_code_for_token(auth_code)
        except requests.exceptions.RequestException:
            return redirect_to_auth_view(request)

        if not token_service.check_token_data_is_valid(token_data):
            try:
                token_info = token_data.keys()
            except AttributeError:
                token_info = token_data
            logger.error("Received invalid token data from TikTok: %s", token_info)
            return redirect_to_auth_view(request)

        # Check if token for user already exists and if yes, delete existing one.
        open_id = token_data.get("open_id")
        if open_id is None:
            logger.error(
                "Received token data without open_id; token_data: %s", token_data
            )
            return redirect_to_auth_view(request)

        token_service.update_or_create_access_token(token_data)

        # Regenerate session ID to prevent session hijacking
        request.session.cycle_key()
        self.port_session.update(tiktok_open_id=open_id)

        return self.redirect_success()

    def redirect_success(self):
        port_context = self.port_session.get_context()
        if port_context == PortabilityContexts.MY_DM:
            return redirect(
                "tiktok_await_data_download"
            )  # TODO: Update when ready to use correct route
        else:
            return redirect("tiktok_await_data_download")


class TikTokAwaitDataDownloadView(
    AuthenticationRequiredMixin,
    ActiveAccessTokenRequiredMixin,
    PortabilitySessionMixin,
    TemplateView,
):
    """Displays a waiting page while TikTok prepares the user's data export.

    This view is intended to show users the status while their data request
    is being processed by TikTok.
    """

    template_name = "portability/tiktok_await_data_download.html"


class TikTokCheckDownloadAvailabilityView(
    ManageAccessTokenMixin,
    PortabilitySessionMixin,
    TemplateView,
):
    """Returns appropriate status for the download availability.

    Returns rendered html partial and intended to be called by an HTMX component.
    """

    template_name = None  # Note: is assigned in get_context_data

    template_pending = "portability/partials/_data_download_pending_msg.html"
    template_success = "portability/partials/_data_download_available_msg.html"
    template_error = "portability/partials/_data_download_error_msg.html"
    template_expired = "portability/partials/_data_download_expired_msg.html"

    def session_dispatch(self, request, *args, **kwargs) -> HttpResponse | None:
        """Redirects unauthenticated requests (open_id not in session)."""
        open_id = self.port_session.get_tiktok_open_id()
        if not open_id:
            msg = "Open ID information missing in session (unauthenticated request)."
            log_security_event(logger, msg, self.request)
            return render(request, self.template_error)

        try:
            access_token = self.get_valid_access_token_from_db(open_id)
        except (TikTokAccessToken.DoesNotExist, ValidationError) as e:
            logger.error("Failed to get access token: %s", e)
            return render(request, self.template_error)

        self.access_token = access_token
        self.access_token.refresh_from_db()
        return super().session_dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Checks data download availability and prepares appropriate template.

        Flow:
        1. Check if a data request already exists for this user
        2. If not, initiate a new data request via TikTok API
        3. Poll the status of the data request
        4. Select appropriate template based on status (pending/success/error)

        Returns:
            dict: Context dictionary containing status information and any
                error messages. The template_name is set based on the status.
        """
        context = super().get_context_data(**kwargs)

        api_client = TikTokPortabilityAPIClient(self.access_token.token)

        # Check if data request has already been issued.
        open_id = self.port_session.get_tiktok_open_id()
        data_request = (
            TikTokDataRequest.objects.filter(
                open_id=open_id,
                download_succeeded=False,
            )
            .exclude(
                status__in=[
                    TikTokDataRequest.State.EXPIRED,
                    TikTokDataRequest.State.CANCELLED,
                ]
            )
            .first()
        )

        if not data_request or not data_request.is_active():
            # Make initial data request.
            response_data = api_client.make_data_request()
            response_valid, msg = api_client.data_request_response_is_valid(
                response_data
            )
            if not response_valid:
                self.template_name = self.template_error
                return context

            data_request = TikTokDataRequest.objects.create(
                open_id=open_id,
                request_id=response_data.get("data", {}).get("request_id"),
            )

        # Poll download status
        request_id = data_request.request_id
        request_status_response = api_client.poll_data_request_status(request_id)
        status_request_valid, msg = (
            api_client.poll_data_request_status_response_is_valid(
                request_status_response
            )
        )

        if not status_request_valid:
            self.template_name = self.template_error
            return context

        # Handle response and update data request object
        request_status_data = request_status_response.get("data")
        request_status = request_status_data.get("status")
        data_request.status = request_status
        data_request.last_polled = timezone.now()
        data_request.save()

        # Use the matching template.
        if request_status == "pending":
            self.template_name = self.template_pending
        elif request_status == "downloading":
            context["request_id"] = request_id
            self.template_name = self.template_success
        elif request_status in ["expired", "cancelled"]:
            self.template_name = self.template_expired
        else:
            self.template_name = self.template_error

        context["poll_datetime"] = timezone.now()

        return context


class TikTokDataDownloadView(
    AuthenticationRequiredMixin,
    ActiveAccessTokenRequiredMixin,
    PortabilitySessionMixin,
    View,
):
    """Handles the actual download of TikTok user data as a ZIP file.

    This view downloads the prepared data from TikTok's API and streams it
    to the user as a downloadable ZIP file.
    """

    def get(self, request, request_id, *args, **kwargs):
        """Downloads and returns the TikTok data as a ZIP file.

        Retrieves the request_id from query parameters, downloads the data
        from TikTok's API, and returns it as an HTTP response with appropriate
        headers for file download.

        Args:
            request: The HTTP request object.
            request_id: The request ID (usually passed as URL path parameter).
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

            Returns:
                HttpResponse: A response containing the ZIP file data with
                    appropriate content-type and content-disposition headers.

            Raises:
                Http404: If the download fails or data is not available.
        """
        open_id = self.port_session.get_tiktok_open_id()

        # Validate request id
        try:
            request_id = int(request_id)
        except ValueError as e:
            log_security_event(
                logger,
                "Received invalid request id",
                self.request,
                extra={
                    "request_id": request_id,
                },
            )

            raise Http404 from e

        # Ensure TikTokDataRequest object exists for the received request ID.
        try:
            data_request = TikTokDataRequest.objects.get(
                request_id=request_id,
                open_id=open_id,
            )
        except TikTokDataRequest.DoesNotExist as e:
            log_security_event(
                logger,
                "Registered attempt to download non-existing request ID",
                self.request,
                extra={
                    "request_id": request_id,
                    "open_id": open_id,
                },
            )

            raise Http404 from e  # TODO: Is there a more adequate option to raise here?

        # Download data
        api_client = TikTokPortabilityAPIClient(self.access_token.token)

        try:
            return api_client.stream_download_requested_data(data_request)
        except Exception:  # noqa: BLE001  TODO: Improve
            return render_http_400(request, "Download Failed")
            # TODO: Is there a more adequate option to raise here?


class TikTokDataReviewView(
    AuthenticationRequiredMixin,
    ActiveAccessTokenRequiredMixin,
    PortabilitySessionMixin,
    TemplateView,
):
    """Gets user information from the TikTok User Info API."""

    template_name = "portability/tiktok_data_review.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_info_retrieved = False

        try:
            response = self.get_user_info_from_tiktok()
        except requests.exceptions.RequestException:
            context["error"] = "request_exception"
            response = None

        if response:
            user_data = response.get("data")
            if user_data:
                user_info = user_data.get("user")
                user_info.pop("union_id", None)
                user_info = self.prettify_user_info(user_info)
                user_info_retrieved = True
            else:
                logger.warning(
                    'Response from TikTok User Info API is missing "data" key.'
                )
                user_info = None

            context["user_info"] = user_info

        context["user_info_retrieved"] = user_info_retrieved
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
        user_info = {"display_name": user_info.pop("display_name"), **user_info}

        for label, value in user_info.items():
            label = label.replace("_", " ").title()
            pretty_dict[label] = value

        return pretty_dict

    def get_user_info_from_tiktok(self, attempt: int = 1) -> dict | None:
        """Retrieves the user information from the TikTok User Info API.

        Args:
            attempt: Number of attempts to get user info.

        Raises:
            RequestException: If the request fails.

        Returns:
            dict | None: The JSON response from the TikTok API endpoint.
                None, if request failed.
        """
        url = settings.TIKTOK_USER_INFO_URL
        fields = ["union_id", "display_name"]
        params = {"fields": ",".join(fields)}
        headers = {"Authorization": f"Bearer {self.access_token.token}"}

        max_tries = 3
        try:
            response = requests.get(
                url, headers=headers, params=params, timeout=(5, 15)
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            # TODO: Handle specific errors.
            # Possible errors: {"error":{"code":"scope_not_authorized",
            # "message":"The user did not authorize the scope required
            # for completing this request.",
            # "log_id":"20250625133420FE910721C437
            # F9AB7B4D"}

            logger.error("Failed to retrieve user info: %s", e)

            if attempt < max_tries:
                time.sleep(3 * attempt)
                return self.get_user_info_from_tiktok(attempt + 1)
            else:
                raise


class TikTokDisconnectView(AuthenticationRequiredMixin, PortabilitySessionMixin, View):
    def get(self, request, *args, **kwargs):
        # Delete open ID from session.
        self.port_session.delete_tiktok_open_id()
        request.session.cycle_key()

        msg = "Successfully disconnected from TikTok."
        return redirect_to_auth_view(request, msg)

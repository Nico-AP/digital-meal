import logging
import time
from datetime import timedelta

import requests

from typing import Tuple

from django.conf import settings
from django.db import transaction
from django.http import StreamingHttpResponse
from django.utils import timezone

from digital_meal.portability.exceptions import TokenRefreshException
from digital_meal.portability.models import TikTokDataRequest, TikTokAccessToken

logger = logging.getLogger(__name__)


class TikTokAccessTokenService:

    def refresh_token(self, access_token: TikTokAccessToken) -> TikTokAccessToken:
        """Refreshes the access token through the TikTok user access token API.

        Raises:
            TokenRefreshException: If token refresh fails.

        Returns:
            TikTokAccessToken: Refreshed token.
        """
        if access_token.refresh_is_expired:
            logger.info(
                'Refresh token expired for TikTokAccessToken %s (expiration date: %s)',
                access_token.pk,
                access_token.refresh_token_expiration_date
            )
            raise TokenRefreshException('Refresh token expired')

        response_data = self._call_tiktok_api(access_token.refresh_token)

        self._update_token(access_token, response_data)
        access_token.refresh_from_db()

        return access_token

    @staticmethod
    def _call_tiktok_api(access_token: TikTokAccessToken) -> dict:
        """Call TikTok API to refresh access token.

        Raises:
            TokenRefreshException: If token refresh fails.

        Returns:
            dict: Refreshed token data.
        """
        url = settings.TIKTOK_TOKEN_URL
        data = {
            'client_key': settings.TIKTOK_CLIENT_KEY,
            'client_secret': settings.TIKTOK_CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': access_token.refresh_token,
        }
        headers = {'Accept': 'application/x-www-form-urlencoded'}

        try:
            response = requests.post(url, data=data, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(
                'Unable to refresh TikTokAccessToken %s: %s', access_token.pk, e
            )
            raise TokenRefreshException(f'Unable to refresh TikTokAccessToken: {e}')

    @staticmethod
    def _update_token(
            access_token: TikTokAccessToken,
            data: dict
    ) -> None:
        """Update the access token with new data."""
        new_expiration_date = timezone.now() + timedelta(seconds=data['expires_in'])
        new_refresh_expiration_date = timezone.now() + timedelta(seconds=data['refresh_expires_in'])

        access_token.token = data['access_token']
        access_token.token_expiration_date = new_expiration_date
        access_token.refresh_token = data['refresh_token']
        access_token.refresh_token_expiration_date = new_refresh_expiration_date
        access_token.token_type = data['token_type']
        access_token.scope = data['scope']
        access_token.save()

    @staticmethod
    def check_token_data_is_valid(token_data: dict) -> bool:
        """Validate the token data structure received from TikTok.

        Check if the received token data is a dictionary and contains the
        expected fields.

        Args:
            token_data: The received token data.

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
    def update_or_create_access_token(token_data: dict) -> TikTokAccessToken:
        """Update or create TikTokAccessToken object from token data dict.

        Args:
            token_data: Dictionary holding the Token information.

        Returns:
            TikTokAccessToken: The newly created TikTokAccessToken object.
        """
        expiration_date = timezone.now() + timedelta(seconds=token_data['expires_in'])
        refresh_expiration_date = timezone.now() + timedelta(seconds=token_data['refresh_expires_in'])
        with transaction.atomic():
            access_token, created = TikTokAccessToken.objects.update_or_create(
                open_id=token_data['open_id'],
                defaults={
                    'token': token_data['access_token'],
                    'token_expiration_date': expiration_date,
                    'refresh_token': token_data['refresh_token'],
                    'refresh_token_expiration_date': refresh_expiration_date,
                    'scope': token_data['scope'],
                    'token_type': token_data['token_type'],
                }
            )
        return access_token

    def exchange_code_for_token(
            self,
            auth_code: str,
            attempt: int = 1,
            max_attempts: int = 3
    ) -> dict:
        """Exchanges the authorization code for an access token and stores it.

        Loads the authorization code received from TikTok from the request
        object and requests the corresponding access token from the TikTok User
        Management API endpoint.

        Args:
            auth_code: Authorization code received from TikTok.
            attempt: Number of attempts to exchange the authorization code.
            max_attempts: Maximum number of attempts to exchange the authorization code.

        Raises:
            requests.exceptions.RequestException: If exchange request fails.

        Returns:
            dict: The JSON response from the TikTok API endpoint.
        """
        url = settings.TIKTOK_TOKEN_URL
        data = {
            'client_key': settings.TIKTOK_CLIENT_KEY,
            'client_secret': settings.TIKTOK_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'redirect_uri': settings.TIKTOK_REDIRECT_URL,
            'code': auth_code
        }
        headers = {'Accept': 'application/json'}

        try:
            response = requests.post(url, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(
                'Request to exchange token timed out (attempt %s)',
                attempt
            )

            if attempt < max_attempts:
                time.sleep(3 * attempt)
                return self.exchange_code_for_token(auth_code, attempt + 1)
            else:
                raise requests.exceptions.RequestException
        except requests.exceptions.RequestException as e:
            logger.error(
                'Failed to retrieve authentication token: %s, (attempt %s)',
                e, attempt
            )

            if attempt < max_attempts:
                time.sleep(3 * attempt)
                return self.exchange_code_for_token(auth_code, attempt + 1)
            else:
                raise


class TikTokPortabilityAPIClient:

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.data_request_url = 'https://open.tiktokapis.com/v2/user/data/add/'
        self.data_request_status_url = 'https://open.tiktokapis.com/v2/user/data/check/'
        self.data_download_url = 'https://open.tiktokapis.com/v2/user/data/download/'

    def make_data_request(self) -> dict:
        """Initiates a data portability request with TikTok's Data Portability API.

        Sends a POST request to TikTok to request all user data in JSON format.
        The data will be prepared asynchronously by TikTok and can be retrieved
        later using the returned request_id.

        Returns:
            dict: JSON response from TikTok containing the following keys:

                'data': {'request_id': <request_id>}

                'error': {'code': <error code>,
                          'message': <error message>,
                          'log_id': <log id>}

        References:
            https://developers.tiktok.com/doc/data-portability-api-add-data-request/
        """
        url = self.data_request_url
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        params = {'fields': 'request_id'}
        payload = {
            'data_format': 'json',
            'category_selection_list': ['all_data']
        }
        try:
            response = requests.post(url, headers=headers, params=params, json=payload)
            response.raise_for_status()
            request_result = response.json()
        except requests.exceptions.RequestException as e:
            logger.error('Failed to make data request: %s', e)
            request_result = {'error': 'Failed to make data request', 'details': e}

        return request_result

    @staticmethod
    def data_request_response_is_valid(response_json: dict) -> Tuple[bool, str]:
        """Validates the response from a TikTok data portability request.

        Checks if:
        - the response contains a valid error code ('ok')
        - response includes the required 'request_id' field

        Args:
            response_json:  The JSON response from TikTok's data request API.

        Returns:
            Tuple[bool, str]: A tuple containing:
                - bool: True if response is valid, False otherwise
                - str: 'ok' if valid, or error message if invalid

        References:
            https://developers.tiktok.com/doc/data-portability-api-add-data-request/#__response
        """
        error_code = response_json.get('error', {}).get('code')
        if error_code != 'ok':
            error_msg = response_json.get('error', {}).get('message')
            msg = f'TikTok data request received invalid error code: {error_msg} (code: {error_code})'
            logger.warning(msg)
            return False, msg

        request_id = response_json.get('data', {}).get('request_id')
        if request_id is None:
            msg = 'Missing "request_id" in TikTok data request response.'
            logger.warning(msg)
            return False, msg

        return True, 'ok'

    def poll_data_request_status(self, request_id: int) -> dict:
        """Polls the status of the portability request with TikTok's API.

        Sends a POST request to TikTok to poll the status of the data request with
        request_id.

        Args:
            request_id: The ID of the data portability request.

        Returns:
            dict: JSON response from TikTok containing information on the
                current status of the data request.

        References:
            https://developers.tiktok.com/doc/data-portability-api-check-status-of-data-request
        """
        url = self.data_request_status_url
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        fields = [
            'request_id',
            'apply_time',
            'collect_time',
            'status',
            'data_format',
            'category_selection_list',
        ]
        params = {'fields': ','.join(fields)}
        payload = {
            'request_id': request_id,
        }
        try:
            response = requests.post(
                url,
                headers=headers,
                params=params,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            poll_result = response.json()
        except requests.exceptions.Timeout:
            logger.error('Data request status polling timed out')
            poll_result = {'error': 'Data request status polling timed out'}
        except requests.exceptions.RequestException as e:
            logger.error(
                'Failed to poll data request status: %s (request_id: %s)',
                e, request_id
            )
            poll_result = {'error': 'Failed to poll data request status'}

        return poll_result

    @staticmethod
    def poll_data_request_status_response_is_valid(response_json: dict) -> Tuple[bool, str]:
        """Validates the response from a TikTok data request status check.

        Checks if:
        - the response contains a valid error code ('ok')
        - response includes the required 'data' field
        - response has a valid status code

        Args:
            response_json: The JSON response from TikTok's status check API.

        Returns:
            Tuple[bool, dict | str]: A tuple or dict containing:
                - bool: True if response is valid, False otherwise
                - str: 'ok' if valid, or error message if invalid

        References:
            https://developers.tiktok.com/doc/data-portability-api-check-status-of-data-request#__response
        """
        error_code = response_json.get('error', {}).get('code')
        if error_code != 'ok':
            error_msg = response_json.get('error', {}).get('message')
            msg = f'TikTok data request status check received invalid error code: {error_msg} (code: {error_code})'
            logger.warning(msg)
            return False, msg

        request_data = response_json.get('data')
        if request_data is None:
            msg = 'Missing "data" in TikTok data request response.'
            logger.warning(msg)
            return False, msg

        valid_status_codes = ['pending', 'downloading', 'expired', 'cancelled']
        status_code = request_data.get('status')
        if status_code not in valid_status_codes:
            msg = f'Invalid status code in TikTok data request response: {status_code}'
            logger.warning(msg)
            return False, msg

        return True, 'ok'

    def stream_download_requested_data(
            self,
            data_request: TikTokDataRequest
    ) -> StreamingHttpResponse:
        """Downloads the requested data from TikTok's Portability API as a stream.

        Sends a POST request to TikTok to download the requested data associated to
        a given data_request (should only be done, after the status for the given
        request is 'downloading' - check using the check_data_request_status()
        function).
        Returns the response.content as a streaming response.

        Args:
            data_request: TikTokDataRequest object.

        Returns:
            StreamingHttpResponse: Data stream retrieved from TikTok.

        References:
            https://developers.tiktok.com/doc/data-portability-api-download
        """
        request_id = data_request.request_id
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        payload = {
            'request_id': request_id,
        }
        try:
            response = requests.post(
                self.data_download_url,
                headers=headers,
                json=payload,
                stream=True
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(
                'Download failed for request %s: %s',
                request_id, e
            )
            raise

        def stream_with_cleanup():
            try:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            except Exception as err:
                data_request.download_succeeded = False
                data_request.save()
                logger.error(
                    'Download failed for request %s: %s',
                    request_id, err
                )
                raise
            else:
                data_request.download_succeeded = True
                data_request.save()
                logger.info(
                    'Download completed successfully for request %s',
                    request_id
                )
            finally:
                # This runs after streaming completes (or fails)
                data_request.download_attempted = True
                data_request.downloaded_at = timezone.now()
                data_request.save()

        streaming_response = StreamingHttpResponse(
            stream_with_cleanup(),
            content_type='application/zip'
        )
        streaming_response['Content-Disposition'] = f'attachment; filename="tiktok_data_{request_id}.zip"'

        return streaming_response

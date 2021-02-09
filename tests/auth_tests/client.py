import re

from django.contrib.auth.views import (
    INTERNAL_RESET_SESSION_TOKEN, PasswordResetConfirmView,
)
from django.test import Client


def extract_token_from_url(url):
    token_search = re.search(r'/reset/.*/(.+?)/', url)
    if token_search:
        return token_search[1]


class PasswordResetConfirmClient(Client):
    """
    This client eases testing the password reset flow by emulating the
    PasswordResetConfirmView's redirect and saving of the reset token in the
    user's session. This request puts 'my-token' in the session and redirects
    to '/reset/bla/set-password/':

    >>> client = PasswordResetConfirmClient()
    >>> client.get('/reset/bla/my-token/')
    """
    reset_url_token = PasswordResetConfirmView.reset_url_token

    def _get_password_reset_confirm_redirect_url(self, url):
        token = extract_token_from_url(url)
        if not token:
            return url
        # Add the token to the session
        session = self.session
        session[INTERNAL_RESET_SESSION_TOKEN] = token
        session.save()
        return url.replace(token, self.reset_url_token)

    def get(self, path, *args, **kwargs):
        redirect_url = self._get_password_reset_confirm_redirect_url(path)
        return super().get(redirect_url, *args, **kwargs)

    def post(self, path, *args, **kwargs):
        redirect_url = self._get_password_reset_confirm_redirect_url(path)
        return super().post(redirect_url, *args, **kwargs)

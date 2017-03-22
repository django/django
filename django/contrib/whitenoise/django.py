from __future__ import absolute_import

import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
try:
    from django.contrib.staticfiles.storage import staticfiles_storage
except ImproperlyConfigured:
    if not os.environ.get('DJANGO_SETTINGS_MODULE'):
        raise ImproperlyConfigured(
                "'DJANGO_SETTINGS_MODULE' environment variable must be set "
                "before importing 'whitenoise.django'")
    else:
        raise
from django.contrib.staticfiles import finders
from django.utils.six.moves.urllib.parse import urlparse

from .base import WhiteNoise
# Import here under an alias for backwards compatibility
from .storage import (CompressedManifestStaticFilesStorage as
                      GzipManifestStaticFilesStorage)
from .utils import (decode_if_byte_string, ensure_leading_trailing_slash,
                    IsDirectoryError)


__all__ = ['DjangoWhiteNoise', 'GzipManifestStaticFilesStorage']


class DjangoWhiteNoise(WhiteNoise):

    config_attrs = WhiteNoise.config_attrs + (
            'root', 'use_finders', 'static_prefix')
    root = None
    use_finders = False
    static_prefix = None

    def __init__(self, application, settings=settings):
        self.configure_from_settings(settings)
        self.check_settings(settings)
        super(DjangoWhiteNoise, self).__init__(application)
        if self.static_root:
            self.add_files(self.static_root, prefix=self.static_prefix)
        if self.root:
            self.add_files(self.root)

    def configure_from_settings(self, settings):
        # Default configuration
        self.charset = settings.FILE_CHARSET
        self.autorefresh = settings.DEBUG
        self.use_finders = settings.DEBUG
        self.static_prefix = urlparse(settings.STATIC_URL or '').path
        if settings.DEBUG:
            self.max_age = 0
        # Allow settings to override default attributes
        for attr in self.config_attrs:
            settings_key = 'WHITENOISE_{0}'.format(attr.upper())
            try:
                value = getattr(settings, settings_key)
            except AttributeError:
                pass
            else:
                value = decode_if_byte_string(value)
                setattr(self, attr, value)
        self.static_prefix = ensure_leading_trailing_slash(self.static_prefix)
        self.static_root = decode_if_byte_string(settings.STATIC_ROOT)

    def check_settings(self, settings):
        if self.use_finders and not self.autorefresh:
            raise ImproperlyConfigured(
                'WHITENOISE_USE_FINDERS can only be enabled in development '
                'when WHITENOISE_AUTOREFRESH is also enabled.'
            )

    def find_file(self, url):
        if self.use_finders and url.startswith(self.static_prefix):
            path = finders.find(url[len(self.static_prefix):])
            if path:
                try:
                    return self.get_static_file(path, url)
                except IsDirectoryError:
                    return None
        return super(DjangoWhiteNoise, self).find_file(url)

    def is_immutable_file(self, path, url):
        """
        Determine whether given URL represents an immutable file (i.e. a
        file with a hash of its contents as part of its name) which can
        therefore be cached forever
        """
        if not url.startswith(self.static_prefix):
            return False
        name = url[len(self.static_prefix):]
        name_without_hash = self.get_name_without_hash(name)
        if name == name_without_hash:
            return False
        static_url = self.get_static_url(name_without_hash)
        # If the static URL function maps the name without hash
        # back to the original URL, then we know we've got a
        # versioned filename
        if static_url and static_url.endswith(url):
            return True
        return False

    def get_name_without_hash(self, filename):
        """
        Removes the version hash from a filename e.g, transforms
        'css/application.f3ea4bcc2.css' into 'css/application.css'

        Note: this is specific to the naming scheme used by Django's
        CachedStaticFilesStorage. You may have to override this if
        you are using a different static files versioning system
        """
        name_with_hash, ext = os.path.splitext(filename)
        name = os.path.splitext(name_with_hash)[0]
        return name + ext

    def get_static_url(self, name):
        try:
            return decode_if_byte_string(staticfiles_storage.url(name))
        except ValueError:
            return None

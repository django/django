import io
import os
import hashlib
import getpass

from base64 import standard_b64encode

from distutils import log
from distutils.command import upload as orig
from distutils.spawn import spawn

from distutils.errors import DistutilsError

from setuptools.extern.six.moves.urllib.request import urlopen, Request
from setuptools.extern.six.moves.urllib.error import HTTPError
from setuptools.extern.six.moves.urllib.parse import urlparse


class upload(orig.upload):
    """
    Override default upload behavior to obtain password
    in a variety of different ways.
    """
    def run(self):
        try:
            orig.upload.run(self)
        finally:
            self.announce(
                "WARNING: Uploading via this command is deprecated, use twine "
                "to upload instead (https://pypi.org/p/twine/)",
                log.WARN
            )

    def finalize_options(self):
        orig.upload.finalize_options(self)
        self.username = (
            self.username or
            getpass.getuser()
        )
        # Attempt to obtain password. Short circuit evaluation at the first
        # sign of success.
        self.password = (
            self.password or
            self._load_password_from_keyring() or
            self._prompt_for_password()
        )

    def upload_file(self, command, pyversion, filename):
        # Makes sure the repository URL is compliant
        schema, netloc, url, params, query, fragments = \
            urlparse(self.repository)
        if params or query or fragments:
            raise AssertionError("Incompatible url %s" % self.repository)

        if schema not in ('http', 'https'):
            raise AssertionError("unsupported schema " + schema)

        # Sign if requested
        if self.sign:
            gpg_args = ["gpg", "--detach-sign", "-a", filename]
            if self.identity:
                gpg_args[2:2] = ["--local-user", self.identity]
            spawn(gpg_args,
                  dry_run=self.dry_run)

        # Fill in the data - send all the meta-data in case we need to
        # register a new release
        with open(filename, 'rb') as f:
            content = f.read()

        meta = self.distribution.metadata

        data = {
            # action
            ':action': 'file_upload',
            'protocol_version': '1',

            # identify release
            'name': meta.get_name(),
            'version': meta.get_version(),

            # file content
            'content': (os.path.basename(filename), content),
            'filetype': command,
            'pyversion': pyversion,
            'md5_digest': hashlib.md5(content).hexdigest(),

            # additional meta-data
            'metadata_version': str(meta.get_metadata_version()),
            'summary': meta.get_description(),
            'home_page': meta.get_url(),
            'author': meta.get_contact(),
            'author_email': meta.get_contact_email(),
            'license': meta.get_licence(),
            'description': meta.get_long_description(),
            'keywords': meta.get_keywords(),
            'platform': meta.get_platforms(),
            'classifiers': meta.get_classifiers(),
            'download_url': meta.get_download_url(),
            # PEP 314
            'provides': meta.get_provides(),
            'requires': meta.get_requires(),
            'obsoletes': meta.get_obsoletes(),
            }

        data['comment'] = ''

        if self.sign:
            data['gpg_signature'] = (os.path.basename(filename) + ".asc",
                                     open(filename+".asc", "rb").read())

        # set up the authentication
        user_pass = (self.username + ":" + self.password).encode('ascii')
        # The exact encoding of the authentication string is debated.
        # Anyway PyPI only accepts ascii for both username or password.
        auth = "Basic " + standard_b64encode(user_pass).decode('ascii')

        # Build up the MIME payload for the POST data
        boundary = '--------------GHSKFJDLGDS7543FJKLFHRE75642756743254'
        sep_boundary = b'\r\n--' + boundary.encode('ascii')
        end_boundary = sep_boundary + b'--\r\n'
        body = io.BytesIO()
        for key, value in data.items():
            title = '\r\nContent-Disposition: form-data; name="%s"' % key
            # handle multiple entries for the same name
            if not isinstance(value, list):
                value = [value]
            for value in value:
                if type(value) is tuple:
                    title += '; filename="%s"' % value[0]
                    value = value[1]
                else:
                    value = str(value).encode('utf-8')
                body.write(sep_boundary)
                body.write(title.encode('utf-8'))
                body.write(b"\r\n\r\n")
                body.write(value)
        body.write(end_boundary)
        body = body.getvalue()

        msg = "Submitting %s to %s" % (filename, self.repository)
        self.announce(msg, log.INFO)

        # build the Request
        headers = {
            'Content-type': 'multipart/form-data; boundary=%s' % boundary,
            'Content-length': str(len(body)),
            'Authorization': auth,
        }

        request = Request(self.repository, data=body,
                          headers=headers)
        # send the data
        try:
            result = urlopen(request)
            status = result.getcode()
            reason = result.msg
        except HTTPError as e:
            status = e.code
            reason = e.msg
        except OSError as e:
            self.announce(str(e), log.ERROR)
            raise

        if status == 200:
            self.announce('Server response (%s): %s' % (status, reason),
                          log.INFO)
            if self.show_response:
                text = getattr(self, '_read_pypi_response',
                               lambda x: None)(result)
                if text is not None:
                    msg = '\n'.join(('-' * 75, text, '-' * 75))
                    self.announce(msg, log.INFO)
        else:
            msg = 'Upload failed (%s): %s' % (status, reason)
            self.announce(msg, log.ERROR)
            raise DistutilsError(msg)

    def _load_password_from_keyring(self):
        """
        Attempt to load password from keyring. Suppress Exceptions.
        """
        try:
            keyring = __import__('keyring')
            return keyring.get_password(self.repository, self.username)
        except Exception:
            pass

    def _prompt_for_password(self):
        """
        Prompt for a password on the tty. Suppress Exceptions.
        """
        try:
            return getpass.getpass()
        except (Exception, KeyboardInterrupt):
            pass

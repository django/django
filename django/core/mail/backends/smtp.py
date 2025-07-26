"""SMTP email backend class."""

import email.policy
import smtplib
import ssl
import threading
from email.headerregistry import Address, AddressHeader

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.utils import DNS_NAME
from django.utils.encoding import force_str, punycode
from django.utils.functional import cached_property


class EmailBackend(BaseEmailBackend):
    """
    A wrapper that manages the SMTP network connection.
    """

    def __init__(
        self,
        host=None,
        port=None,
        username=None,
        password=None,
        use_tls=None,
        fail_silently=False,
        use_ssl=None,
        timeout=None,
        ssl_keyfile=None,
        ssl_certfile=None,
        **kwargs,
    ):
        super().__init__(fail_silently=fail_silently)
        self.host = host or settings.EMAIL_HOST
        self.port = port or settings.EMAIL_PORT
        self.username = settings.EMAIL_HOST_USER if username is None else username
        self.password = settings.EMAIL_HOST_PASSWORD if password is None else password
        self.use_tls = settings.EMAIL_USE_TLS if use_tls is None else use_tls
        self.use_ssl = settings.EMAIL_USE_SSL if use_ssl is None else use_ssl
        self.timeout = settings.EMAIL_TIMEOUT if timeout is None else timeout
        self.ssl_keyfile = (
            settings.EMAIL_SSL_KEYFILE if ssl_keyfile is None else ssl_keyfile
        )
        self.ssl_certfile = (
            settings.EMAIL_SSL_CERTFILE if ssl_certfile is None else ssl_certfile
        )
        if self.use_ssl and self.use_tls:
            raise ValueError(
                "EMAIL_USE_TLS/EMAIL_USE_SSL are mutually exclusive, so only set "
                "one of those settings to True."
            )
        self.connection = None
        self._lock = threading.RLock()

    @property
    def connection_class(self):
        return smtplib.SMTP_SSL if self.use_ssl else smtplib.SMTP

    @cached_property
    def ssl_context(self):
        if self.ssl_certfile or self.ssl_keyfile:
            ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.load_cert_chain(self.ssl_certfile, self.ssl_keyfile)
            return ssl_context
        else:
            return ssl.create_default_context()

    def open(self):
        """
        Ensure an open connection to the email server. Return whether or not a
        new connection was required (True or False) or None if an exception
        passed silently.
        """
        if self.connection:
            # Nothing to do if the connection is already open.
            return False

        # If local_hostname is not specified, socket.getfqdn() gets used.
        # For performance, we use the cached FQDN for local_hostname.
        connection_params = {"local_hostname": DNS_NAME.get_fqdn()}
        if self.timeout is not None:
            connection_params["timeout"] = self.timeout
        if self.use_ssl:
            connection_params["context"] = self.ssl_context
        try:
            self.connection = self.connection_class(
                self.host, self.port, **connection_params
            )

            # TLS/SSL are mutually exclusive, so only attempt TLS over
            # non-secure connections.
            if not self.use_ssl and self.use_tls:
                self.connection.starttls(context=self.ssl_context)
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except OSError:
            if not self.fail_silently:
                raise

    def close(self):
        """Close the connection to the email server."""
        if self.connection is None:
            return
        try:
            try:
                self.connection.quit()
            except (ssl.SSLError, smtplib.SMTPServerDisconnected):
                # This happens when calling quit() on a TLS connection
                # sometimes, or when the connection was already disconnected
                # by the server.
                self.connection.close()
            except smtplib.SMTPException:
                if self.fail_silently:
                    return
                raise
        finally:
            self.connection = None

    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects and return the number of email
        messages sent.
        """
        if not email_messages:
            return 0
        with self._lock:
            new_conn_created = self.open()
            if not self.connection or new_conn_created is None:
                # We failed silently on open().
                # Trying to send would be pointless.
                return 0
            num_sent = 0
            try:
                for message in email_messages:
                    sent = self._send(message)
                    if sent:
                        num_sent += 1
            finally:
                if new_conn_created:
                    self.close()
        return num_sent

    def _send(self, email_message):
        """A helper method that does the actual sending."""
        if not email_message.recipients():
            return False
        from_email = self.prep_address(email_message.from_email)
        recipients = [self.prep_address(addr) for addr in email_message.recipients()]
        message = email_message.message(policy=email.policy.SMTP)
        try:
            self.connection.sendmail(from_email, recipients, message.as_bytes())
        except smtplib.SMTPException:
            if not self.fail_silently:
                raise
            return False
        return True

    def prep_address(self, address, force_ascii=True):
        """
        Return the addr-spec portion of an email address. Raises ValueError for
        invalid addresses, including CR/NL injection.

        If force_ascii is True, apply IDNA encoding to non-ASCII domains, and
        raise ValueError for non-ASCII local-parts (which can't be encoded).
        Otherwise, leave Unicode characters unencoded (e.g., for sending with
        SMTPUTF8).
        """
        address = force_str(address)
        parsed = AddressHeader.value_parser(address)
        defects = set(str(defect) for defect in parsed.all_defects)
        # Django allows local mailboxes like "From: webmaster" (#15042).
        defects.discard("addr-spec local part with no domain")
        if not force_ascii:
            # Non-ASCII local-part is valid with SMTPUTF8. Remove once
            # https://github.com/python/cpython/issues/81074 is fixed.
            defects.discard("local-part contains non-ASCII characters)")
        if defects:
            raise ValueError(f"Invalid address {address!r}: {'; '.join(defects)}")

        mailboxes = parsed.all_mailboxes
        if len(mailboxes) != 1:
            raise ValueError(f"Invalid address {address!r}: must be a single address")

        mailbox = mailboxes[0]
        if force_ascii and mailbox.domain and not mailbox.domain.isascii():
            # Re-compose an addr-spec with the IDNA encoded domain.
            domain = punycode(mailbox.domain)
            return str(Address(username=mailbox.local_part, domain=domain))
        else:
            return mailbox.addr_spec

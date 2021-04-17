"""Module containing the implementation of the URIMixin class."""
import warnings

from . import exceptions as exc
from . import misc
from . import normalizers
from . import validators


class URIMixin(object):
    """Mixin with all shared methods for URIs and IRIs."""

    __hash__ = tuple.__hash__

    def authority_info(self):
        """Return a dictionary with the ``userinfo``, ``host``, and ``port``.

        If the authority is not valid, it will raise a
        :class:`~rfc3986.exceptions.InvalidAuthority` Exception.

        :returns:
            ``{'userinfo': 'username:password', 'host': 'www.example.com',
            'port': '80'}``
        :rtype: dict
        :raises rfc3986.exceptions.InvalidAuthority:
            If the authority is not ``None`` and can not be parsed.
        """
        if not self.authority:
            return {'userinfo': None, 'host': None, 'port': None}

        match = self._match_subauthority()

        if match is None:
            # In this case, we have an authority that was parsed from the URI
            # Reference, but it cannot be further parsed by our
            # misc.SUBAUTHORITY_MATCHER. In this case it must not be a valid
            # authority.
            raise exc.InvalidAuthority(self.authority.encode(self.encoding))

        # We had a match, now let's ensure that it is actually a valid host
        # address if it is IPv4
        matches = match.groupdict()
        host = matches.get('host')

        if (host and misc.IPv4_MATCHER.match(host) and not
                validators.valid_ipv4_host_address(host)):
            # If we have a host, it appears to be IPv4 and it does not have
            # valid bytes, it is an InvalidAuthority.
            raise exc.InvalidAuthority(self.authority.encode(self.encoding))

        return matches

    def _match_subauthority(self):
        return misc.SUBAUTHORITY_MATCHER.match(self.authority)

    @property
    def host(self):
        """If present, a string representing the host."""
        try:
            authority = self.authority_info()
        except exc.InvalidAuthority:
            return None
        return authority['host']

    @property
    def port(self):
        """If present, the port extracted from the authority."""
        try:
            authority = self.authority_info()
        except exc.InvalidAuthority:
            return None
        return authority['port']

    @property
    def userinfo(self):
        """If present, the userinfo extracted from the authority."""
        try:
            authority = self.authority_info()
        except exc.InvalidAuthority:
            return None
        return authority['userinfo']

    def is_absolute(self):
        """Determine if this URI Reference is an absolute URI.

        See http://tools.ietf.org/html/rfc3986#section-4.3 for explanation.

        :returns: ``True`` if it is an absolute URI, ``False`` otherwise.
        :rtype: bool
        """
        return bool(misc.ABSOLUTE_URI_MATCHER.match(self.unsplit()))

    def is_valid(self, **kwargs):
        """Determine if the URI is valid.

        .. deprecated:: 1.1.0

            Use the :class:`~rfc3986.validators.Validator` object instead.

        :param bool require_scheme: Set to ``True`` if you wish to require the
            presence of the scheme component.
        :param bool require_authority: Set to ``True`` if you wish to require
            the presence of the authority component.
        :param bool require_path: Set to ``True`` if you wish to require the
            presence of the path component.
        :param bool require_query: Set to ``True`` if you wish to require the
            presence of the query component.
        :param bool require_fragment: Set to ``True`` if you wish to require
            the presence of the fragment component.
        :returns: ``True`` if the URI is valid. ``False`` otherwise.
        :rtype: bool
        """
        warnings.warn("Please use rfc3986.validators.Validator instead. "
                      "This method will be eventually removed.",
                      DeprecationWarning)
        validators = [
            (self.scheme_is_valid, kwargs.get('require_scheme', False)),
            (self.authority_is_valid, kwargs.get('require_authority', False)),
            (self.path_is_valid, kwargs.get('require_path', False)),
            (self.query_is_valid, kwargs.get('require_query', False)),
            (self.fragment_is_valid, kwargs.get('require_fragment', False)),
            ]
        return all(v(r) for v, r in validators)

    def authority_is_valid(self, require=False):
        """Determine if the authority component is valid.

        .. deprecated:: 1.1.0

            Use the :class:`~rfc3986.validators.Validator` object instead.

        :param bool require:
            Set to ``True`` to require the presence of this component.
        :returns:
            ``True`` if the authority is valid. ``False`` otherwise.
        :rtype:
            bool
        """
        warnings.warn("Please use rfc3986.validators.Validator instead. "
                      "This method will be eventually removed.",
                      DeprecationWarning)
        try:
            self.authority_info()
        except exc.InvalidAuthority:
            return False

        return validators.authority_is_valid(
            self.authority,
            host=self.host,
            require=require,
        )

    def scheme_is_valid(self, require=False):
        """Determine if the scheme component is valid.

        .. deprecated:: 1.1.0

            Use the :class:`~rfc3986.validators.Validator` object instead.

        :param str require: Set to ``True`` to require the presence of this
            component.
        :returns: ``True`` if the scheme is valid. ``False`` otherwise.
        :rtype: bool
        """
        warnings.warn("Please use rfc3986.validators.Validator instead. "
                      "This method will be eventually removed.",
                      DeprecationWarning)
        return validators.scheme_is_valid(self.scheme, require)

    def path_is_valid(self, require=False):
        """Determine if the path component is valid.

        .. deprecated:: 1.1.0

            Use the :class:`~rfc3986.validators.Validator` object instead.

        :param str require: Set to ``True`` to require the presence of this
            component.
        :returns: ``True`` if the path is valid. ``False`` otherwise.
        :rtype: bool
        """
        warnings.warn("Please use rfc3986.validators.Validator instead. "
                      "This method will be eventually removed.",
                      DeprecationWarning)
        return validators.path_is_valid(self.path, require)

    def query_is_valid(self, require=False):
        """Determine if the query component is valid.

        .. deprecated:: 1.1.0

            Use the :class:`~rfc3986.validators.Validator` object instead.

        :param str require: Set to ``True`` to require the presence of this
            component.
        :returns: ``True`` if the query is valid. ``False`` otherwise.
        :rtype: bool
        """
        warnings.warn("Please use rfc3986.validators.Validator instead. "
                      "This method will be eventually removed.",
                      DeprecationWarning)
        return validators.query_is_valid(self.query, require)

    def fragment_is_valid(self, require=False):
        """Determine if the fragment component is valid.

        .. deprecated:: 1.1.0

            Use the Validator object instead.

        :param str require: Set to ``True`` to require the presence of this
            component.
        :returns: ``True`` if the fragment is valid. ``False`` otherwise.
        :rtype: bool
        """
        warnings.warn("Please use rfc3986.validators.Validator instead. "
                      "This method will be eventually removed.",
                      DeprecationWarning)
        return validators.fragment_is_valid(self.fragment, require)

    def normalized_equality(self, other_ref):
        """Compare this URIReference to another URIReference.

        :param URIReference other_ref: (required), The reference with which
            we're comparing.
        :returns: ``True`` if the references are equal, ``False`` otherwise.
        :rtype: bool
        """
        return tuple(self.normalize()) == tuple(other_ref.normalize())

    def resolve_with(self, base_uri, strict=False):
        """Use an absolute URI Reference to resolve this relative reference.

        Assuming this is a relative reference that you would like to resolve,
        use the provided base URI to resolve it.

        See http://tools.ietf.org/html/rfc3986#section-5 for more information.

        :param base_uri: Either a string or URIReference. It must be an
            absolute URI or it will raise an exception.
        :returns: A new URIReference which is the result of resolving this
            reference using ``base_uri``.
        :rtype: :class:`URIReference`
        :raises rfc3986.exceptions.ResolutionError:
            If the ``base_uri`` is not an absolute URI.
        """
        if not isinstance(base_uri, URIMixin):
            base_uri = type(self).from_string(base_uri)

        if not base_uri.is_absolute():
            raise exc.ResolutionError(base_uri)

        # This is optional per
        # http://tools.ietf.org/html/rfc3986#section-5.2.1
        base_uri = base_uri.normalize()

        # The reference we're resolving
        resolving = self

        if not strict and resolving.scheme == base_uri.scheme:
            resolving = resolving.copy_with(scheme=None)

        # http://tools.ietf.org/html/rfc3986#page-32
        if resolving.scheme is not None:
            target = resolving.copy_with(
                path=normalizers.normalize_path(resolving.path)
            )
        else:
            if resolving.authority is not None:
                target = resolving.copy_with(
                    scheme=base_uri.scheme,
                    path=normalizers.normalize_path(resolving.path)
                )
            else:
                if resolving.path is None:
                    if resolving.query is not None:
                        query = resolving.query
                    else:
                        query = base_uri.query
                    target = resolving.copy_with(
                        scheme=base_uri.scheme,
                        authority=base_uri.authority,
                        path=base_uri.path,
                        query=query
                    )
                else:
                    if resolving.path.startswith('/'):
                        path = normalizers.normalize_path(resolving.path)
                    else:
                        path = normalizers.normalize_path(
                            misc.merge_paths(base_uri, resolving.path)
                        )
                    target = resolving.copy_with(
                        scheme=base_uri.scheme,
                        authority=base_uri.authority,
                        path=path,
                        query=resolving.query
                    )
        return target

    def unsplit(self):
        """Create a URI string from the components.

        :returns: The URI Reference reconstituted as a string.
        :rtype: str
        """
        # See http://tools.ietf.org/html/rfc3986#section-5.3
        result_list = []
        if self.scheme:
            result_list.extend([self.scheme, ':'])
        if self.authority:
            result_list.extend(['//', self.authority])
        if self.path:
            result_list.append(self.path)
        if self.query is not None:
            result_list.extend(['?', self.query])
        if self.fragment is not None:
            result_list.extend(['#', self.fragment])
        return ''.join(result_list)

    def copy_with(self, scheme=misc.UseExisting, authority=misc.UseExisting,
                  path=misc.UseExisting, query=misc.UseExisting,
                  fragment=misc.UseExisting):
        """Create a copy of this reference with the new components.

        :param str scheme:
            (optional) The scheme to use for the new reference.
        :param str authority:
            (optional) The authority to use for the new reference.
        :param str path:
            (optional) The path to use for the new reference.
        :param str query:
            (optional) The query to use for the new reference.
        :param str fragment:
            (optional) The fragment to use for the new reference.
        :returns:
            New URIReference with provided components.
        :rtype:
            URIReference
        """
        attributes = {
            'scheme': scheme,
            'authority': authority,
            'path': path,
            'query': query,
            'fragment': fragment,
        }
        for key, value in list(attributes.items()):
            if value is misc.UseExisting:
                del attributes[key]
        uri = self._replace(**attributes)
        uri.encoding = self.encoding
        return uri

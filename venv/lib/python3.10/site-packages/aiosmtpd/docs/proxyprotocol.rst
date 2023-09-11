.. _ProxyProtocol:

========================
 PROXY Protocol Support
========================

When put behind a "proxy" / load balancer,
server programs can no longer "see" the original client's actual IP Address and Port.

This also affects ``aiosmtpd``.

The |HAProxyDevelopers|_ have created a protocol called "PROXY Protocol"
designed to solve this issue.
You can read the reasoning behind this in `their blog`_.

.. _`HAProxyDevelopers`: https://www.haproxy.com/company/about-us/
.. |HAProxyDevelopers| replace:: **HAProxy Developers**
.. _their blog: https://www.haproxy.com/blog/haproxy/proxy-protocol/

This initiative has been accepted and supported by many important software and services
such as `Amazon Web Services`_, `HAProxy`_, `NGINX`_, `stunnel`_, `Varnish`_, and many others.

.. _Amazon Web Services: https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/enable-proxy-protocol.html
.. _HAProxy: http://cbonte.github.io/haproxy-dconv/2.3/configuration.html#5.2-send-proxy
.. _NGINX: https://nginx.org/en/docs/stream/ngx_stream_proxy_module.html#proxy_protocol
.. _stunnel: https://www.stunnel.org/static/stunnel.html#proxy
.. _Varnish: https://info.varnish-software.com/blog/proxy-protocol-original-value-client-identity

``aiosmtpd`` implements the PROXY Protocol as defined in the documentation accompanying |HAProxy2.3.0|_;
*both* Version 1 and Version 2 are supported.

.. _HAProxy2.3.0: https://github.com/haproxy/haproxy/blob/v2.3.0/doc/proxy-protocol.txt
.. |HAProxy2.3.0| replace:: **HAProxy v2.3.0**


Activating
==========

To activate ``aiosmtpd``'s PROXY Protocol Support,
you have to set the :attr:`proxy_protocol_timeout` parameter of the SMTP Class
to a positive numeric value (``int`` or ``float``)

The `PROXY Protocol documentation suggests`_ that the timeout should not be less than 3.0 seconds.

.. _PROXY Protocol documentation suggests: https://github.com/haproxy/haproxy/blob/v2.3.0/doc/proxy-protocol.txt#L172-L174

.. important::

   Once you activate PROXY Protocol support,
   standard (E)SMTP handshake is **no longer available**.

   Clients trying to connect to ``aiosmtpd`` will be REQUIRED
   to send the PROXY Protocol Header
   before they can continue with (E)SMTP transaction.

   This is `as specified`_ in the PROXY Protocol documentation.

.. _as specified: https://github.com/haproxy/haproxy/blob/v2.3.0/doc/proxy-protocol.txt#L176-L180


``handle_PROXY`` Hook
=====================

In addition to activating the PROXY protocol support as described above,
you MUST implement the ``handle_PROXY`` hook.
If the :attr:`handler` object does not implement ``handle_PROXY``,
then all connection attempts will be rejected.

The signature of ``handle_PROXY`` must be as follows:

.. method:: handle_PROXY(server, session, envelope, proxy_data)

   :param server: The :class:`SMTP` instance invoking the hook.
   :type server: aiosmtpd.smtp.SMTP
   :param session: The Session data *so far* (see Important note below)
   :type session: Session
   :param envelope: The Envelope data *so far* (see Important note below)
   :type envelope: Envelope
   :param proxy_data: The result of parsing the PROXY Header
   :type proxy_data: ProxyData
   :return: Truthy or Falsey, indicating if the connection may continue or not, respectively

   .. important::

      The ``session.peer`` attribute will contain the ``IP:port`` information
      of the **directly adjacent** client.
      In other word,
      it will contain the endpoint identifier of the proxying entity.

      Endpoint identifier of the "original" client will be recorded
      *only* in the :attr:`proxy_data` parameter

      The ``envelope`` data will usually be empty(ish),
      because the PROXY handshake will take place before
      client can send any transaction data.


Parsing the Header
==================

You do not have to concern yourself with parsing the PROXY Protocol header;
the ``aiosmtpd.proxy_protocol`` module contains the full parsing logic.

All you need to do is to *validate* the parsed result in the ``handle_PROXY`` hook.

.. py:module:: aiosmtpd.proxy_protocol

Enums
=====

.. class:: AF

   .. py:attribute:: \
      UNSPEC = 0
      IP4 = 1
      IP6 = 2
      UNIX = 3

   For Version 1, ``UNKNOWN`` is mapped to ``UNSPEC``.

.. class:: PROTO

   .. py:attribute:: \
      UNSPEC = 0
      STREAM = 1
      DGRAM = 2

   For Version 1, ``UNKNOWN`` is mapped to ``UNSPEC``, and ``TCP`` is mapped into ``STREAM``

.. class:: V2_CMD

   .. py:attribute:: \
      LOCAL = 0
      PROXY = 1


``ProxyData`` API
=================

.. py:class:: ProxyData(\
   version=None\
   )

   |
   | :part:`Attributes & Properties`

   .. py:attribute:: version
      :type: Optional[int]

      Contains the version of the PROXY Protocol header.

      If ``None``, it indicates that parsing has failed and the header is malformed.

   .. py:attribute:: command
      :type: V2_CMD

      Contains the `command`_. Only set if ``version=2``

   .. py:attribute:: family
      :type: AF

      Contains the `address family`_.

      Valid values for Version 1 excludes :attr:`AF.UNIX`.

   .. py:attribute:: protocol
      :type: PROTO

      Contains an integer indicating the `transport protocol being proxied`_.

      Valid values for Version 1 excludes :attr:`PROTO.DGRAM`.

   .. py:attribute:: src_addr
      :type: Union[IPv4Address, IPv6Address, AnyStr]

      Contains the source address
      (i.e., address of the "original" client).

      The type of this attribute depends on the :attr:`address family <family>`.

   .. py:attribute:: dst_addr
      :type: Union[IPv4Address, IPv6Address, AnyStr]

      Contains the destination address
      (i.e., address of the proxying entity to which the "original" client connected).

      The type of this attribute depends on the address family.

   .. py:attribute:: src_port
      :type: int

      Contains the source port
      (i.e., port of the "original" client).

      Valid only for address family of :attr:`AF.INET` or :attr:`AF.INET6`

   .. py:attribute:: dst_port
      :type: int

      Contains the destination port
      (i.e., port of the proxying entity to which the "original" client connected).

      Valid only for address family of :attr:`AF.INET` or :attr:`AF.INET6`

   .. py:attribute:: rest
      :type: ByteString

      The contents depend on the version of the PROXY header *and* (for version 2)
      the address family.

      For PROXY Header version 1,
      it contains all the bytes following ``b"UNKNOWN"`` up until, but not including,
      the ``CRLF`` terminator.

      For PROXY Header version 2:

        * For address family ``UNSPEC``,
          it contains all the bytes following the 16-octet header preamble
        * For address families :attr:`AF.INET`, :attr:`AF.INET6`, and :attr:`AF.UNIX`
          it contains all the bytes following the address information

   .. py:attribute:: tlv
      :type: aiosmtpd.proxy_protocol.ProxyTLV

      This property contains the result of the TLV Parsing attempt of the :attr:`rest` attribute.

      If this property returns ``None`` that means either
      (1) :attr:`rest` is empty, or
      (2) TLV Parsing is not successful.

   .. py:attribute:: valid
      :type: bool

      This property will indicate if PROXY Header is valid or not.

   .. py:attribute:: whole_raw
      :type: bytearray

      This attribute contains the whole, undecoded and unmodified, PROXY Header.
      For version 1, it contains everything up to and including the terminating ``\r\n``.
      For version 2, it contains everything up to and including the last TLV Vector.

      If you need to verify the ``CRC32C`` TLV Vector (PROXYv2),
      you should run the CRC32C calculation against the contents of this attribute.
      For more information, see the next section, :ref:`crc32c`.

   .. py:attribute:: tlv_start
      :type: int

      This attribute points to the first TLV Vector *if exists*.

      If you need to verify the ``CRC32C`` TLV Vector,
      you should run the CRC32C calculation against the contents of this attribute.

      The value will be ``None`` if PROXY version is 1.

   |
   | :part:`Methods`

   .. py:method:: with_error(error_msg: str) -> ProxyData

      :param str error_msg: Error message
      :return: self

      Sets the instance's :attr:`error` attribute and returns itself.

   .. py:method:: same_attribs(_raises=False, **kwargs) -> bool

      :param _raises: If ``True``, raise exception if attribute not match/not found,
         instead of returning a bool. Defaults to ``False``
      :type _raises: bool
      :raises ValueError: if ``_raises=True`` and attribute is found but value is wrong
      :raises KeyError: if ``_raises=True`` and attribute is not found

      A helper method to quickly verify whether an attribute exists
      and contain the same value as expected.

      Example usage::

         proxy_data.same_attribs(
             version=1,
             protocol=b"TCP4",
             unknown_attrib=None
         )

      In the above example,
      ``same_attribs`` will check that all attributes
      ``version``, ``protocol``, and ``unknown_attrib`` exist,
      and contains the values ``1``, ``b"TCP4"``, and ``None``, respectively.

      Missing attributes and/or differing values will return a ``False``
      (unless ``_raises=True``)

      .. note::

         For other examples, take a look inside the ``test_proxyprotocol.py`` file.
         That file *extensively* uses ``same_attribs``.

   .. py:method:: __bool__()

      Allows an instance of ``ProxyData`` to be evaluated as boolean.
      In actuality, it simply returns the :attr:`valid` property.


``ProxyTLV`` API
================

.. py:class:: ProxyTLV()

   This class parses the `TLV portion`_ of the PROXY Header
   and presents the value in an easy-to-use way:
   A "TLV Vector" whose "Type" is found in :attr:`PP2_TYPENAME`
   can be accessed through the `.<NAME>` attribute.

   It is a subclass of :class:`dict`,
   so all of ``dict``'s methods are available.
   It is basically a `Dict[str, Any]` with additional methods and attributes.
   The list below only describes methods & attributes added to this class.

   .. py:attribute:: PP2_TYPENAME
      :type: Dict[int, str]

      A mapping of numeric Type to a human-friendly Name.

      The names are identical to the ones `listed in the documentation`_,
      but with the ``PP2_TYPE_``/``PP2_SUBTYPE_`` prefixes removed.

      .. note::

         The ``SSL`` Name is special.
         Rather than containing the TLV Subvectors as described in the standard,
         it is a ``bool`` value that indicates whether the PP2_SUBTYPE_SSL

   .. py:attribute:: tlv_loc
      :type: Dict[str, int]

      A mapping to show the start location of certain TLV Vectors.

      The keys are the TYPENAME (see :attr:`PP2_TYPENAME` above),
      and the value is the offset from start of the TLV Vectors.

   .. py:method:: same_attribs(_raises=False, **kwargs) -> bool

      :param _raises: If ``True``, raise exception if attribute not match/not found,
         instead of returning a bool. Defaults to ``False``
      :type _raises: bool
      :raises ValueError: if ``_raises=True`` and attribute is found but value is wrong
      :raises KeyError: if ``_raises=True`` and attribute is not found

      A helper method to quickly verify whether an attribute exists
      and contain the same value as expected.

      Example usage::

         assert isinstance(proxy_tlv, ProxyTLV)
         proxy_tlv.same_attribs(
             AUTHORITY=b"some_authority",
             SSL=True,
         )

      In the above example,
      ``same_attribs`` will check that the attributes
      ``AUTHORITY`` and ``SSL`` exist,
      and contains the values ``b"some_authority"`` and ``True``, respectively.

      Missing attributes and/or differing values will return a ``False``
      (unless ``_raises=True``)

      .. note::

         For other examples, take a look inside the ``test_proxyprotocol.py`` file.
         That file *extensively* uses ``same_attribs``.

   .. py:classmethod:: from_raw(raw) -> Optional[ProxyTLV]

      :param raw: The raw bytes containing the TLV Vectors
      :type raw: ByteString
      :return: A new instance of ProxyTLV, or ``None`` if parsing failed

      This triggers the parsing of raw bytes/bytearray into a ProxyTLV instance.

      Internally it relies on the :meth:`parse` classmethod to perform the parsing.

      Unlike the default behavior of :meth:`parse`,
      ``from_raw`` will NOT perform a partial parsing.

   .. py:classmethod:: parse(chunk, partial_ok=True) -> Dict[str, Any]

      :param chunk: The bytes to parse into TLV Vectors
      :type chunk: ByteString
      :param partial_ok: If ``True``, return partially-parsed TLV Vectors as is.
         If ``False``, (re)raise ``MalformedTLV``
      :type partial_ok: bool
      :return: A mapping of typenames and values

      This performs a recursive parsing of the bytes.
      If it encounters a TYPE that ProxyTLV doesn't recognize,
      the TLV Vector will be assigned a typename of `"xNN"`

      Partial parsing is possible when ``partial_ok=True``;
      if during the parsing an error happened,
      `parse` will abort returning the TLV Vectors it had successfully decoded.

   .. py:classmethod:: name_to_num(name) -> Optional[int]

      :param name: The name to back-map into TYPE numeric
      :type name: str
      :return: The numeric value associated to the typename, ``None`` if no such mapping is found

      This is a helper method to perform back-mapping of typenames.

.. _crc32c:

Note on CRC32C Calculation
==========================

Neither the :class:`ProxyData` nor :class:`ProxyTLV` classes implement `PROXYv2 CRC32C validation`_;
the main reason being that Python has no built-in module for calculating CRC32C.
To perform CRC32C, third-party modules need to be installed,
but we are uncomfortable doing that for the following reasons:

* There are more than one third-party modules providing CRC32C,
  e.g., ``crcmod``, ``crc32c``, ``google-crc32c``, etc.
  Problem is, there is no known clear comparison between them,
  so we cannot tell easily which one is 'best'.
* Some of these third-party modules seem to be no longer being maintained.
* Most of the available third-party modules are binary distribution.
  This potentially causes problems with existing binaries/libraries,
  not to mention possible (albeit unlikely) vector for malware.
* We really don't like adding dependencies outside those that are really needed.

In short, we have strong reasons to NOT implement PROXYv2 CRC32C validation,
and we have plans to NEVER implement it.

If you *absolutely* need PROXYv2 CRC32C validation,
you should perform it yourself in the :meth:`handle_PROXY` hook.
To assist you, we have provided the :attr:`whole_raw`, :attr:`tlv_start`, and :attr:`tlv_loc` attributes.

You should do the following:

0. Choose a CRC32C module of your liking, install that, and import it.

1. Find the "CRC32C" TLV Vector in ``whole_raw``;
   it would start at byte ``tlv_start + tlv_loc["CRC32C"]``

2. Zero out the 4-octet Value part of the "CRC32C" TLV Vector

3. Perform CRC32C calculation over the modified ``whole_raw``

4. Convert the result to big-endian bytes,
   and compare with the ``.CRC32C`` attribute of the ProxyTLV instance

Example::

    # The int(3) at end is to skip over the "T" and "L" part
    offset = proxy_data.tlv_start + proxy_data.tlv.tlv_loc["CRC32C"] + 3
    # Since whole_raw is a bytearray, we can do slice replacement
    proxy_data.whole_raw[offset:offset + 4] = "\x00\x00\x00\x00"
    # Actual syntax will depend on the module you use
    calculated: int = crc32c(proxy_data.whole_raw)
    # Adjust first part as necessary if calculated is not int
    validated = calculated.to_bytes(4, "big") == proxy_data.tlv.CRC32C

Good luck!

.. _`command`: https://github.com/haproxy/haproxy/blob/v2.3.0/doc/proxy-protocol.txt#L346-L358
.. _`address family`: https://github.com/haproxy/haproxy/blob/v2.3.0/doc/proxy-protocol.txt#L366-L381
.. _`INET protocol and family`:  https://github.com/haproxy/haproxy/blob/v2.3.0/doc/proxy-protocol.txt#L207-L213
.. _`transport protocol being proxied`: https://github.com/haproxy/haproxy/blob/v2.3.0/doc/proxy-protocol.txt#L388-L402
.. _TLV portion: https://github.com/haproxy/haproxy/blob/v2.3.0/doc/proxy-protocol.txt#L519
.. _listed in the documentation: https://github.com/haproxy/haproxy/blob/v2.3.0/doc/proxy-protocol.txt#L538-L549
.. _PROXYv2 CRC32C validation: https://github.com/haproxy/haproxy/blob/v2.3.0/doc/proxy-protocol.txt#L574-L597

"""The database reader for MaxMind MMDB files."""

from __future__ import annotations

import inspect
from typing import IO, TYPE_CHECKING, AnyStr, cast

import maxminddb
from maxminddb import (
    MODE_AUTO,
    MODE_FD,
    MODE_FILE,
    MODE_MEMORY,
    MODE_MMAP,
    MODE_MMAP_EXT,
    InvalidDatabaseError,
)

import geoip2
import geoip2.errors
import geoip2.models

if TYPE_CHECKING:
    import os
    from collections.abc import Sequence

    from typing_extensions import Self

    from geoip2.models import (
        ASN,
        ISP,
        AnonymousIP,
        AnonymousPlus,
        City,
        ConnectionType,
        Country,
        Domain,
        Enterprise,
    )
    from geoip2.types import IPAddress

__all__ = [
    "MODE_AUTO",
    "MODE_FD",
    "MODE_FILE",
    "MODE_MEMORY",
    "MODE_MMAP",
    "MODE_MMAP_EXT",
    "Reader",
]


class Reader:
    """GeoIP2 database Reader object.

    Instances of this class provide a reader for the GeoIP2 database format.
    IP addresses can be looked up using the ``country`` and ``city`` methods.

    The basic API for this class is the same for every database. First, you
    create a reader object, specifying a file name or file descriptor.
    You then call the method corresponding to the specific database, passing
    it the IP address you want to look up.

    If the request succeeds, the method call will return a model class for the
    method you called. This model in turn contains multiple record classes,
    each of which represents part of the data returned by the database. If the
    database does not contain the requested information, the attributes on the
    record class will have a ``None`` value.

    If the address is not in the database, an
    ``geoip2.errors.AddressNotFoundError`` exception will be thrown. If the
    database is corrupt or invalid, a ``maxminddb.InvalidDatabaseError`` will
    be thrown.
    """

    def __init__(
        self,
        fileish: (
            AnyStr | int | os.PathLike[str] | os.PathLike[bytes] | IO[str] | IO[bytes]
        ),
        locales: Sequence[str] | None = None,
        mode: int = MODE_AUTO,
    ) -> None:
        """Create GeoIP2 Reader.

        :param fileish: A path to the GeoIP2 database or an existing file
          descriptor pointing to the database. Note that a file descriptor
          is only valid when mode is MODE_FD.
        :param locales: This is list of locale codes. This argument will be
          passed on to record classes to use when their name properties are
          called. The default value is ['en'].

          The order of the locales is significant. When a record class has
          multiple names (country, city, etc.), its name property will return
          the name in the first locale that has one.

          Note that the only locale which is always present in the GeoIP2
          data is "en". If you do not include this locale, the name property
          may end up returning None even when the record has an English name.

          Currently, the valid locale codes are:

          * de -- German
          * en -- English names may still include accented characters if that
            is the accepted spelling in English. In other words, English does
            not mean ASCII.
          * es -- Spanish
          * fr -- French
          * ja -- Japanese
          * pt-BR -- Brazilian Portuguese
          * ru -- Russian
          * zh-CN -- Simplified Chinese.
        :param mode: The mode to open the database with. Valid mode are:
          * MODE_MMAP_EXT - use the C extension with memory map.
          * MODE_MMAP - read from memory map. Pure Python.
          * MODE_FILE - read database as standard file. Pure Python.
          * MODE_MEMORY - load database into memory. Pure Python.
          * MODE_FD - the param passed via fileish is a file descriptor, not a
             path. This mode implies MODE_MEMORY. Pure Python.
          * MODE_AUTO - try MODE_MMAP_EXT, MODE_MMAP, MODE_FILE in that order.
             Default.

        """
        if locales is None:
            locales = ["en"]
        self._db_reader = maxminddb.open_database(fileish, mode)
        self._db_type = self._db_reader.metadata().database_type
        self._locales = locales

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def country(self, ip_address: IPAddress) -> Country:
        """Get the Country object for the IP address.

        :param ip_address: IPv4 or IPv6 address as a string.

        :returns: :py:class:`geoip2.models.Country` object

        """
        return cast(
            "Country",
            self._model_for(geoip2.models.Country, "Country", ip_address),
        )

    def city(self, ip_address: IPAddress) -> City:
        """Get the City object for the IP address.

        :param ip_address: IPv4 or IPv6 address as a string.

        :returns: :py:class:`geoip2.models.City` object

        """
        return cast("City", self._model_for(geoip2.models.City, "City", ip_address))

    def anonymous_ip(self, ip_address: IPAddress) -> AnonymousIP:
        """Get the AnonymousIP object for the IP address.

        :param ip_address: IPv4 or IPv6 address as a string.

        :returns: :py:class:`geoip2.models.AnonymousIP` object

        """
        return cast(
            "AnonymousIP",
            self._flat_model_for(
                geoip2.models.AnonymousIP,
                "GeoIP2-Anonymous-IP",
                ip_address,
            ),
        )

    def anonymous_plus(self, ip_address: IPAddress) -> AnonymousPlus:
        """Get the AnonymousPlus object for the IP address.

        :param ip_address: IPv4 or IPv6 address as a string.

        :returns: :py:class:`geoip2.models.AnonymousPlus` object

        """
        return cast(
            "AnonymousPlus",
            self._flat_model_for(
                geoip2.models.AnonymousPlus,
                "GeoIP-Anonymous-Plus",
                ip_address,
            ),
        )

    def asn(self, ip_address: IPAddress) -> ASN:
        """Get the ASN object for the IP address.

        :param ip_address: IPv4 or IPv6 address as a string.

        :returns: :py:class:`geoip2.models.ASN` object

        """
        return cast(
            "ASN",
            self._flat_model_for(geoip2.models.ASN, "GeoLite2-ASN", ip_address),
        )

    def connection_type(self, ip_address: IPAddress) -> ConnectionType:
        """Get the ConnectionType object for the IP address.

        :param ip_address: IPv4 or IPv6 address as a string.

        :returns: :py:class:`geoip2.models.ConnectionType` object

        """
        return cast(
            "ConnectionType",
            self._flat_model_for(
                geoip2.models.ConnectionType,
                "GeoIP2-Connection-Type",
                ip_address,
            ),
        )

    def domain(self, ip_address: IPAddress) -> Domain:
        """Get the Domain object for the IP address.

        :param ip_address: IPv4 or IPv6 address as a string.

        :returns: :py:class:`geoip2.models.Domain` object

        """
        return cast(
            "Domain",
            self._flat_model_for(geoip2.models.Domain, "GeoIP2-Domain", ip_address),
        )

    def enterprise(self, ip_address: IPAddress) -> Enterprise:
        """Get the Enterprise object for the IP address.

        :param ip_address: IPv4 or IPv6 address as a string.

        :returns: :py:class:`geoip2.models.Enterprise` object

        """
        return cast(
            "Enterprise",
            self._model_for(geoip2.models.Enterprise, "Enterprise", ip_address),
        )

    def isp(self, ip_address: IPAddress) -> ISP:
        """Get the ISP object for the IP address.

        :param ip_address: IPv4 or IPv6 address as a string.

        :returns: :py:class:`geoip2.models.ISP` object

        """
        return cast(
            "ISP",
            self._flat_model_for(geoip2.models.ISP, "GeoIP2-ISP", ip_address),
        )

    def _get(self, database_type: str, ip_address: IPAddress) -> tuple[dict, int]:
        if database_type not in self._db_type:
            caller = inspect.stack()[2][3]
            msg = (
                f"The {caller} method cannot be used with the {self._db_type} database"
            )
            raise TypeError(
                msg,
            )
        (record, prefix_len) = self._db_reader.get_with_prefix_len(ip_address)
        if record is None:
            msg = f"The address {ip_address} is not in the database."
            raise geoip2.errors.AddressNotFoundError(
                msg,
                str(ip_address),
                prefix_len,
            )
        if not isinstance(record, dict):
            msg = f"Expected record to be a dict but was f{type(record)}"
            raise InvalidDatabaseError(msg)
        return record, prefix_len

    def _model_for(
        self,
        model_class: type[City | Country | Enterprise],
        types: str,
        ip_address: IPAddress,
    ) -> City | Country | Enterprise:
        (record, prefix_len) = self._get(types, ip_address)
        return model_class(
            self._locales,
            ip_address=ip_address,
            prefix_len=prefix_len,
            **record,
        )

    def _flat_model_for(
        self,
        model_class: type[Domain | ISP | ConnectionType | ASN | AnonymousIP],
        types: str,
        ip_address: IPAddress,
    ) -> ConnectionType | ISP | AnonymousIP | Domain | ASN:
        (record, prefix_len) = self._get(types, ip_address)
        return model_class(ip_address, prefix_len=prefix_len, **record)

    def metadata(
        self,
    ) -> maxminddb.reader.Metadata:
        """Get the metadata for the open database.

        :returns: :py:class:`maxminddb.reader.Metadata` object
        """
        return self._db_reader.metadata()

    def close(self) -> None:
        """Close the GeoIP2 database."""
        self._db_reader.close()

"""
maxminddb.extension
~~~~~~~~~~~~~~~~

This module contains the C extension database reader and related classes.

"""

from ipaddress import IPv4Address, IPv6Address
from os import PathLike
from typing import Any, AnyStr, Dict, IO, List, Optional, Tuple, Union
from maxminddb import MODE_AUTO
from maxminddb.types import Record

class Reader:
    """
    A C extension implementation of a reader for the MaxMind DB format. IP
    addresses can be looked up using the ``get`` method.
    """

    closed: bool = ...

    def __init__(
        self, database: Union[AnyStr, int, PathLike, IO], mode: int = MODE_AUTO
    ) -> None:
        """Reader for the MaxMind DB file format

        Arguments:
        database -- A path to a valid MaxMind DB file such as a GeoIP2 database
                    file, or a file descriptor in the case of MODE_FD.
        mode -- mode to open the database with. The only supported modes are
                MODE_AUTO and MODE_MMAP_EXT.
        """

    def close(self) -> None:
        """Closes the MaxMind DB file and returns the resources to the system"""

    def get(self, ip_address: Union[str, IPv6Address, IPv4Address]) -> Optional[Record]:
        """Return the record for the ip_address in the MaxMind DB


        Arguments:
        ip_address -- an IP address in the standard string notation
        """

    def get_with_prefix_len(
        self, ip_address: Union[str, IPv6Address, IPv4Address]
    ) -> Tuple[Optional[Record], int]:
        """Return a tuple with the record and the associated prefix length


        Arguments:
        ip_address -- an IP address in the standard string notation
        """

    def metadata(self) -> "Metadata":
        """Return the metadata associated with the MaxMind DB file"""

    def __enter__(self) -> "Reader": ...
    def __exit__(self, *args) -> None: ...

# pylint: disable=too-few-public-methods
class Metadata:
    """Metadata for the MaxMind DB reader"""

    binary_format_major_version: int
    """
    The major version number of the binary format used when creating the
    database.
    """

    binary_format_minor_version: int
    """
    The minor version number of the binary format used when creating the
    database.
    """

    build_epoch: int
    """
    The Unix epoch for the build time of the database.
    """

    database_type: str
    """
    A string identifying the database type, e.g., "GeoIP2-City".
    """

    description: Dict[str, str]
    """
    A map from locales to text descriptions of the database.
    """

    ip_version: int
    """
    The IP version of the data in a database. A value of "4" means the
    database only supports IPv4. A database with a value of "6" may support
    both IPv4 and IPv6 lookups.
    """

    languages: List[str]
    """
    A list of locale codes supported by the databse.
    """

    node_count: int
    """
    The number of nodes in the database.
    """

    record_size: int
    """
    The bit size of a record in the search tree.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Creates new Metadata object. kwargs are key/value pairs from spec"""

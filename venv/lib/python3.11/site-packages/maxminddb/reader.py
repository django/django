"""
maxminddb.reader
~~~~~~~~~~~~~~~~

This module contains the pure Python database reader and related classes.

"""
try:
    import mmap
except ImportError:
    # pylint: disable=invalid-name
    mmap = None  # type: ignore

import ipaddress
import struct
from ipaddress import IPv4Address, IPv6Address
from os import PathLike
from typing import Any, AnyStr, IO, Optional, Tuple, Union

from maxminddb.const import MODE_AUTO, MODE_MMAP, MODE_FILE, MODE_MEMORY, MODE_FD
from maxminddb.decoder import Decoder
from maxminddb.errors import InvalidDatabaseError
from maxminddb.file import FileBuffer
from maxminddb.types import Record

_IPV4_MAX_NUM = 2**32


class Reader:
    """
    Instances of this class provide a reader for the MaxMind DB format. IP
    addresses can be looked up using the ``get`` method.
    """

    _DATA_SECTION_SEPARATOR_SIZE = 16
    _METADATA_START_MARKER = b"\xAB\xCD\xEFMaxMind.com"

    _buffer: Union[bytes, FileBuffer, "mmap.mmap"]
    _buffer_size: int
    closed: bool
    _decoder: Decoder
    _metadata: "Metadata"
    _ipv4_start: int

    def __init__(
        self, database: Union[AnyStr, int, PathLike, IO], mode: int = MODE_AUTO
    ) -> None:
        """Reader for the MaxMind DB file format

        Arguments:
        database -- A path to a valid MaxMind DB file such as a GeoIP2 database
                    file, or a file descriptor in the case of MODE_FD.
        mode -- mode to open the database with. Valid mode are:
            * MODE_MMAP - read from memory map.
            * MODE_FILE - read database as standard file.
            * MODE_MEMORY - load database into memory.
            * MODE_AUTO - tries MODE_MMAP and then MODE_FILE. Default.
            * MODE_FD - the param passed via database is a file descriptor, not
                        a path. This mode implies MODE_MEMORY.
        """
        filename: Any
        if (mode == MODE_AUTO and mmap) or mode == MODE_MMAP:
            with open(database, "rb") as db_file:  # type: ignore
                self._buffer = mmap.mmap(db_file.fileno(), 0, access=mmap.ACCESS_READ)
                self._buffer_size = self._buffer.size()
            filename = database
        elif mode in (MODE_AUTO, MODE_FILE):
            self._buffer = FileBuffer(database)  # type: ignore
            self._buffer_size = self._buffer.size()
            filename = database
        elif mode == MODE_MEMORY:
            with open(database, "rb") as db_file:  # type: ignore
                buf = db_file.read()
                self._buffer = buf
                self._buffer_size = len(buf)
            filename = database
        elif mode == MODE_FD:
            self._buffer = database.read()  # type: ignore
            self._buffer_size = len(self._buffer)  # type: ignore
            filename = database.name  # type: ignore
        else:
            raise ValueError(
                f"Unsupported open mode ({mode}). Only MODE_AUTO, MODE_FILE, "
                "MODE_MEMORY and MODE_FD are supported by the pure Python "
                "Reader"
            )

        metadata_start = self._buffer.rfind(
            self._METADATA_START_MARKER, max(0, self._buffer_size - 128 * 1024)
        )

        if metadata_start == -1:
            self.close()
            raise InvalidDatabaseError(
                f"Error opening database file ({filename}). "
                "Is this a valid MaxMind DB file?"
            )

        metadata_start += len(self._METADATA_START_MARKER)
        metadata_decoder = Decoder(self._buffer, metadata_start)
        (metadata, _) = metadata_decoder.decode(metadata_start)

        if not isinstance(metadata, dict):
            raise InvalidDatabaseError(
                f"Error reading metadata in database file ({filename})."
            )

        self._metadata = Metadata(**metadata)  # pylint: disable=bad-option-value

        self._decoder = Decoder(
            self._buffer,
            self._metadata.search_tree_size + self._DATA_SECTION_SEPARATOR_SIZE,
        )
        self.closed = False

        ipv4_start = 0
        if self._metadata.ip_version == 6:
            # We store the IPv4 starting node as an optimization for IPv4 lookups
            # in IPv6 trees. This allows us to skip over the first 96 nodes in
            # this case.
            node = 0
            for _ in range(96):
                if node >= self._metadata.node_count:
                    break
                node = self._read_node(node, 0)
            ipv4_start = node
        self._ipv4_start = ipv4_start

    def metadata(self) -> "Metadata":
        """Return the metadata associated with the MaxMind DB file"""
        return self._metadata

    def get(self, ip_address: Union[str, IPv6Address, IPv4Address]) -> Optional[Record]:
        """Return the record for the ip_address in the MaxMind DB


        Arguments:
        ip_address -- an IP address in the standard string notation
        """
        (record, _) = self.get_with_prefix_len(ip_address)
        return record

    def get_with_prefix_len(
        self, ip_address: Union[str, IPv6Address, IPv4Address]
    ) -> Tuple[Optional[Record], int]:
        """Return a tuple with the record and the associated prefix length


        Arguments:
        ip_address -- an IP address in the standard string notation
        """
        if isinstance(ip_address, str):
            address = ipaddress.ip_address(ip_address)
        else:
            address = ip_address

        try:
            packed_address = bytearray(address.packed)
        except AttributeError as ex:
            raise TypeError("argument 1 must be a string or ipaddress object") from ex

        if address.version == 6 and self._metadata.ip_version == 4:
            raise ValueError(
                f"Error looking up {ip_address}. You attempted to look up "
                "an IPv6 address in an IPv4-only database."
            )

        (pointer, prefix_len) = self._find_address_in_tree(packed_address)

        if pointer:
            return self._resolve_data_pointer(pointer), prefix_len
        return None, prefix_len

    def __iter__(self):
        return self._generate_children(0, 0, 0)

    def _generate_children(self, node, depth, ip_acc):
        if ip_acc != 0 and node == self._ipv4_start:
            # Skip nodes aliased to IPv4
            return

        node_count = self._metadata.node_count
        if node > node_count:
            bits = 128 if self._metadata.ip_version == 6 else 32
            ip_acc <<= bits - depth
            if ip_acc <= _IPV4_MAX_NUM and bits == 128:
                depth -= 96
            yield ipaddress.ip_network((ip_acc, depth)), self._resolve_data_pointer(
                node
            )
        elif node < node_count:
            left = self._read_node(node, 0)
            ip_acc <<= 1
            depth += 1
            yield from self._generate_children(left, depth, ip_acc)
            right = self._read_node(node, 1)
            yield from self._generate_children(right, depth, ip_acc | 1)

    def _find_address_in_tree(self, packed: bytearray) -> Tuple[int, int]:
        bit_count = len(packed) * 8
        node = self._start_node(bit_count)
        node_count = self._metadata.node_count

        i = 0
        while i < bit_count and node < node_count:
            bit = 1 & (packed[i >> 3] >> 7 - (i % 8))
            node = self._read_node(node, bit)
            i = i + 1

        if node == node_count:
            # Record is empty
            return 0, i
        if node > node_count:
            return node, i

        raise InvalidDatabaseError("Invalid node in search tree")

    def _start_node(self, length: int) -> int:
        if self._metadata.ip_version == 6 and length == 32:
            return self._ipv4_start
        return 0

    def _read_node(self, node_number: int, index: int) -> int:
        base_offset = node_number * self._metadata.node_byte_size

        record_size = self._metadata.record_size
        if record_size == 24:
            offset = base_offset + index * 3
            node_bytes = b"\x00" + self._buffer[offset : offset + 3]
        elif record_size == 28:
            offset = base_offset + 3 * index
            node_bytes = bytearray(self._buffer[offset : offset + 4])
            if index:
                node_bytes[0] = 0x0F & node_bytes[0]
            else:
                middle = (0xF0 & node_bytes.pop()) >> 4
                node_bytes.insert(0, middle)
        elif record_size == 32:
            offset = base_offset + index * 4
            node_bytes = self._buffer[offset : offset + 4]
        else:
            raise InvalidDatabaseError(f"Unknown record size: {record_size}")
        return struct.unpack(b"!I", node_bytes)[0]

    def _resolve_data_pointer(self, pointer: int) -> Record:
        resolved = pointer - self._metadata.node_count + self._metadata.search_tree_size

        if resolved >= self._buffer_size:
            raise InvalidDatabaseError("The MaxMind DB file's search tree is corrupt")

        (data, _) = self._decoder.decode(resolved)
        return data

    def close(self) -> None:
        """Closes the MaxMind DB file and returns the resources to the system"""
        try:
            self._buffer.close()  # type: ignore
        except AttributeError:
            pass
        self.closed = True

    def __exit__(self, *args) -> None:
        self.close()

    def __enter__(self) -> "Reader":
        if self.closed:
            raise ValueError("Attempt to reopen a closed MaxMind DB")
        return self


class Metadata:
    """Metadata for the MaxMind DB reader


    .. attribute:: binary_format_major_version

      The major version number of the binary format used when creating the
      database.

      :type: int

    .. attribute:: binary_format_minor_version

      The minor version number of the binary format used when creating the
      database.

      :type: int

    .. attribute:: build_epoch

      The Unix epoch for the build time of the database.

      :type: int

    .. attribute:: database_type

      A string identifying the database type, e.g., "GeoIP2-City".

      :type: str

    .. attribute:: description

      A map from locales to text descriptions of the database.

      :type: dict(str, str)

    .. attribute:: ip_version

      The IP version of the data in a database. A value of "4" means the
      database only supports IPv4. A database with a value of "6" may support
      both IPv4 and IPv6 lookups.

      :type: int

    .. attribute:: languages

      A list of locale codes supported by the databse.

      :type: list(str)

    .. attribute:: node_count

      The number of nodes in the database.

      :type: int

    .. attribute:: record_size

      The bit size of a record in the search tree.

      :type: int

    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self, **kwargs) -> None:
        """Creates new Metadata object. kwargs are key/value pairs from spec"""
        # Although I could just update __dict__, that is less obvious and it
        # doesn't work well with static analysis tools and some IDEs
        self.node_count = kwargs["node_count"]
        self.record_size = kwargs["record_size"]
        self.ip_version = kwargs["ip_version"]
        self.database_type = kwargs["database_type"]
        self.languages = kwargs["languages"]
        self.binary_format_major_version = kwargs["binary_format_major_version"]
        self.binary_format_minor_version = kwargs["binary_format_minor_version"]
        self.build_epoch = kwargs["build_epoch"]
        self.description = kwargs["description"]

    @property
    def node_byte_size(self) -> int:
        """The size of a node in bytes

        :type: int
        """
        return self.record_size // 4

    @property
    def search_tree_size(self) -> int:
        """The size of the search tree

        :type: int
        """
        return self.node_count * self.node_byte_size

    def __repr__(self):
        args = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__module__}.{self.__class__.__name__}({args})"

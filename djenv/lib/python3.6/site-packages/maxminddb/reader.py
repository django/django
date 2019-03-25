"""
maxminddb.reader
~~~~~~~~~~~~~~~~

This module contains the pure Python database reader and related classes.

"""
from __future__ import unicode_literals

try:
    import mmap
except ImportError:
    # pylint: disable=invalid-name
    mmap = None

import struct

from maxminddb.compat import (byte_from_int, compat_ip_address, string_type,
                              string_type_name)
from maxminddb.const import MODE_AUTO, MODE_MMAP, MODE_FILE, MODE_MEMORY, MODE_FD
from maxminddb.decoder import Decoder
from maxminddb.errors import InvalidDatabaseError
from maxminddb.file import FileBuffer


class Reader(object):
    """
    Instances of this class provide a reader for the MaxMind DB format. IP
    addresses can be looked up using the ``get`` method.
    """

    _DATA_SECTION_SEPARATOR_SIZE = 16
    _METADATA_START_MARKER = b"\xAB\xCD\xEFMaxMind.com"

    _ipv4_start = None

    def __init__(self, database, mode=MODE_AUTO):
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
        if (mode == MODE_AUTO and mmap) or mode == MODE_MMAP:
            with open(database, 'rb') as db_file:
                self._buffer = mmap.mmap(
                    db_file.fileno(), 0, access=mmap.ACCESS_READ)
                self._buffer_size = self._buffer.size()
            filename = database
        elif mode in (MODE_AUTO, MODE_FILE):
            self._buffer = FileBuffer(database)
            self._buffer_size = self._buffer.size()
            filename = database
        elif mode == MODE_MEMORY:
            with open(database, 'rb') as db_file:
                self._buffer = db_file.read()
                self._buffer_size = len(self._buffer)
            filename = database
        elif mode == MODE_FD:
            self._buffer = database.read()
            self._buffer_size = len(self._buffer)
            filename = database.name
        else:
            raise ValueError(
                'Unsupported open mode ({0}). Only MODE_AUTO, MODE_FILE, '
                'MODE_MEMORY and MODE_FD are supported by the pure Python '
                'Reader'.format(mode))

        metadata_start = self._buffer.rfind(
            self._METADATA_START_MARKER, max(0,
                                             self._buffer_size - 128 * 1024))

        if metadata_start == -1:
            self.close()
            raise InvalidDatabaseError('Error opening database file ({0}). '
                                       'Is this a valid MaxMind DB file?'
                                       ''.format(filename))

        metadata_start += len(self._METADATA_START_MARKER)
        metadata_decoder = Decoder(self._buffer, metadata_start)
        (metadata, _) = metadata_decoder.decode(metadata_start)
        self._metadata = Metadata(**metadata)  # pylint: disable=bad-option-value

        self._decoder = Decoder(self._buffer, self._metadata.search_tree_size +
                                self._DATA_SECTION_SEPARATOR_SIZE)
        self.closed = False

    def metadata(self):
        """Return the metadata associated with the MaxMind DB file"""
        return self._metadata

    def get(self, ip_address):
        """Return the record for the ip_address in the MaxMind DB


        Arguments:
        ip_address -- an IP address in the standard string notation
        """
        if not isinstance(ip_address, string_type):
            raise TypeError('argument 1 must be %s, not %s' %
                            (string_type_name, type(ip_address).__name__))

        address = compat_ip_address(ip_address)

        if address.version == 6 and self._metadata.ip_version == 4:
            raise ValueError(
                'Error looking up {0}. You attempted to look up '
                'an IPv6 address in an IPv4-only database.'.format(ip_address))
        pointer = self._find_address_in_tree(address)

        return self._resolve_data_pointer(pointer) if pointer else None

    def _find_address_in_tree(self, ip_address):
        packed = bytearray(ip_address.packed)

        bit_count = len(packed) * 8
        node = self._start_node(bit_count)

        for i in range(bit_count):
            if node >= self._metadata.node_count:
                break
            bit = 1 & (packed[i >> 3] >> 7 - (i % 8))
            node = self._read_node(node, bit)
        if node == self._metadata.node_count:
            # Record is empty
            return 0
        elif node > self._metadata.node_count:
            return node

        raise InvalidDatabaseError('Invalid node in search tree')

    def _start_node(self, length):
        if self._metadata.ip_version != 6 or length == 128:
            return 0

        # We are looking up an IPv4 address in an IPv6 tree. Skip over the
        # first 96 nodes.
        if self._ipv4_start:
            return self._ipv4_start

        node = 0
        for _ in range(96):
            if node >= self._metadata.node_count:
                break
            node = self._read_node(node, 0)
        self._ipv4_start = node
        return node

    def _read_node(self, node_number, index):
        base_offset = node_number * self._metadata.node_byte_size

        record_size = self._metadata.record_size
        if record_size == 24:
            offset = base_offset + index * 3
            node_bytes = b'\x00' + self._buffer[offset:offset + 3]
        elif record_size == 28:
            (middle, ) = struct.unpack(
                b'!B', self._buffer[base_offset + 3:base_offset + 4])
            if index:
                middle &= 0x0F
            else:
                middle = (0xF0 & middle) >> 4
            offset = base_offset + index * 4
            node_bytes = byte_from_int(middle) + self._buffer[offset:offset + 3]
        elif record_size == 32:
            offset = base_offset + index * 4
            node_bytes = self._buffer[offset:offset + 4]
        else:
            raise InvalidDatabaseError(
                'Unknown record size: {0}'.format(record_size))
        return struct.unpack(b'!I', node_bytes)[0]

    def _resolve_data_pointer(self, pointer):
        resolved = pointer - self._metadata.node_count + \
            self._metadata.search_tree_size

        if resolved > self._buffer_size:
            raise InvalidDatabaseError(
                "The MaxMind DB file's search tree is corrupt")

        (data, _) = self._decoder.decode(resolved)
        return data

    def close(self):
        """Closes the MaxMind DB file and returns the resources to the system"""
        # pylint: disable=unidiomatic-typecheck
        if type(self._buffer) not in (str, bytes):
            self._buffer.close()
        self.closed = True

    def __exit__(self, *args):
        self.close()

    def __enter__(self):
        if self.closed:
            raise ValueError('Attempt to reopen a closed MaxMind DB')
        return self


class Metadata(object):
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
    def __init__(self, **kwargs):
        """Creates new Metadata object. kwargs are key/value pairs from spec"""
        # Although I could just update __dict__, that is less obvious and it
        # doesn't work well with static analysis tools and some IDEs
        self.node_count = kwargs['node_count']
        self.record_size = kwargs['record_size']
        self.ip_version = kwargs['ip_version']
        self.database_type = kwargs['database_type']
        self.languages = kwargs['languages']
        self.binary_format_major_version = kwargs[
            'binary_format_major_version']
        self.binary_format_minor_version = kwargs[
            'binary_format_minor_version']
        self.build_epoch = kwargs['build_epoch']
        self.description = kwargs['description']

    @property
    def node_byte_size(self):
        """The size of a node in bytes

        :type: int
        """
        return self.record_size // 4

    @property
    def search_tree_size(self):
        """The size of the search tree

        :type: int
        """
        return self.node_count * self.node_byte_size

    def __repr__(self):
        args = ', '.join('%s=%r' % x for x in self.__dict__.items())
        return '{module}.{class_name}({data})'.format(
            module=self.__module__,
            class_name=self.__class__.__name__,
            data=args)

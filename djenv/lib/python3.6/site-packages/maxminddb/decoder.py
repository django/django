"""
maxminddb.decoder
~~~~~~~~~~~~~~~~~

This package contains code for decoding the MaxMind DB data section.

"""
from __future__ import unicode_literals

import struct

from maxminddb.compat import byte_from_int, int_from_bytes
from maxminddb.errors import InvalidDatabaseError


class Decoder(object):  # pylint: disable=too-few-public-methods
    """Decoder for the data section of the MaxMind DB"""

    def __init__(self, database_buffer, pointer_base=0, pointer_test=False):
        """Created a Decoder for a MaxMind DB

        Arguments:
        database_buffer -- an mmap'd MaxMind DB file.
        pointer_base -- the base number to use when decoding a pointer
        pointer_test -- used for internal unit testing of pointer code
        """
        self._pointer_test = pointer_test
        self._buffer = database_buffer
        self._pointer_base = pointer_base

    def _decode_array(self, size, offset):
        array = []
        for _ in range(size):
            (value, offset) = self.decode(offset)
            array.append(value)
        return array, offset

    def _decode_boolean(self, size, offset):
        return size != 0, offset

    def _decode_bytes(self, size, offset):
        new_offset = offset + size
        return self._buffer[offset:new_offset], new_offset

    # pylint: disable=no-self-argument
    # |-> I am open to better ways of doing this as long as it doesn't involve
    #     lots of code duplication.
    def _decode_packed_type(type_code, type_size, pad=False):
        # pylint: disable=protected-access, missing-docstring
        def unpack_type(self, size, offset):
            if not pad:
                self._verify_size(size, type_size)
            new_offset = offset + size
            packed_bytes = self._buffer[offset:new_offset]
            if pad:
                packed_bytes = packed_bytes.rjust(type_size, b'\x00')
            (value, ) = struct.unpack(type_code, packed_bytes)
            return value, new_offset

        return unpack_type

    def _decode_map(self, size, offset):
        container = {}
        for _ in range(size):
            (key, offset) = self.decode(offset)
            (value, offset) = self.decode(offset)
            container[key] = value
        return container, offset

    _pointer_value_offset = {
        1: 0,
        2: 2048,
        3: 526336,
        4: 0,
    }

    def _decode_pointer(self, size, offset):
        pointer_size = ((size >> 3) & 0x3) + 1
        new_offset = offset + pointer_size
        pointer_bytes = self._buffer[offset:new_offset]
        packed = pointer_bytes if pointer_size == 4 else struct.pack(
            b'!c', byte_from_int(size & 0x7)) + pointer_bytes
        unpacked = int_from_bytes(packed)
        pointer = unpacked + self._pointer_base + \
            self._pointer_value_offset[pointer_size]
        if self._pointer_test:
            return pointer, new_offset
        (value, _) = self.decode(pointer)
        return value, new_offset

    def _decode_uint(self, size, offset):
        new_offset = offset + size
        uint_bytes = self._buffer[offset:new_offset]
        return int_from_bytes(uint_bytes), new_offset

    def _decode_utf8_string(self, size, offset):
        new_offset = offset + size
        return self._buffer[offset:new_offset].decode('utf-8'), new_offset

    _type_decoder = {
        1: _decode_pointer,
        2: _decode_utf8_string,
        3: _decode_packed_type(b'!d', 8),  # double,
        4: _decode_bytes,
        5: _decode_uint,  # uint16
        6: _decode_uint,  # uint32
        7: _decode_map,
        8: _decode_packed_type(b'!i', 4, pad=True),  # int32
        9: _decode_uint,  # uint64
        10: _decode_uint,  # uint128
        11: _decode_array,
        14: _decode_boolean,
        15: _decode_packed_type(b'!f', 4),  # float,
    }

    def decode(self, offset):
        """Decode a section of the data section starting at offset

        Arguments:
        offset -- the location of the data structure to decode
        """
        new_offset = offset + 1
        (ctrl_byte, ) = struct.unpack(b'!B', self._buffer[offset:new_offset])
        type_num = ctrl_byte >> 5
        # Extended type
        if not type_num:
            (type_num, new_offset) = self._read_extended(new_offset)

        if type_num not in self._type_decoder:
            raise InvalidDatabaseError('Unexpected type number ({type}) '
                                       'encountered'.format(type=type_num))

        (size, new_offset) = self._size_from_ctrl_byte(ctrl_byte, new_offset,
                                                       type_num)
        return self._type_decoder[type_num](self, size, new_offset)

    def _read_extended(self, offset):
        (next_byte, ) = struct.unpack(b'!B', self._buffer[offset:offset + 1])
        type_num = next_byte + 7
        if type_num < 7:
            raise InvalidDatabaseError(
                'Something went horribly wrong in the decoder. An '
                'extended type resolved to a type number < 8 '
                '({type})'.format(type=type_num))
        return type_num, offset + 1

    def _verify_size(self, expected, actual):
        if expected != actual:
            raise InvalidDatabaseError(
                'The MaxMind DB file\'s data section contains bad data '
                '(unknown data type or corrupt data)')

    def _size_from_ctrl_byte(self, ctrl_byte, offset, type_num):
        size = ctrl_byte & 0x1f
        if type_num == 1:
            return size, offset
        bytes_to_read = 0 if size < 29 else size - 28

        new_offset = offset + bytes_to_read
        size_bytes = self._buffer[offset:new_offset]

        # Using unpack rather than int_from_bytes as it is about 200 lookups
        # per second faster here.
        if size == 29:
            size = 29 + struct.unpack(b'!B', size_bytes)[0]
        elif size == 30:
            size = 285 + struct.unpack(b'!H', size_bytes)[0]
        elif size > 30:
            size = struct.unpack(b'!I', size_bytes.rjust(4,
                                                         b'\x00'))[0] + 65821

        return size, new_offset

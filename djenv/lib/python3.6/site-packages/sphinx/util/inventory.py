# -*- coding: utf-8 -*-
"""
    sphinx.util.inventory
    ~~~~~~~~~~~~~~~~~~~~~

    Inventory utility functions for Sphinx.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
import os
import re
import zlib

from six import PY3

from sphinx.util import logging

if False:
    # For type annotation
    from typing import Callable, Dict, IO, Iterator, Tuple  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA

    if PY3:
        unicode = str

    Inventory = Dict[unicode, Dict[unicode, Tuple[unicode, unicode, unicode, unicode]]]


BUFSIZE = 16 * 1024
logger = logging.getLogger(__name__)


class InventoryFileReader(object):
    """A file reader for inventory file.

    This reader supports mixture of texts and compressed texts.
    """

    def __init__(self, stream):
        # type: (IO) -> None
        self.stream = stream
        self.buffer = b''
        self.eof = False

    def read_buffer(self):
        # type: () -> None
        chunk = self.stream.read(BUFSIZE)
        if chunk == b'':
            self.eof = True
        self.buffer += chunk

    def readline(self):
        # type: () -> unicode
        pos = self.buffer.find(b'\n')
        if pos != -1:
            line = self.buffer[:pos].decode('utf-8')
            self.buffer = self.buffer[pos + 1:]
        elif self.eof:
            line = self.buffer.decode('utf-8')
            self.buffer = b''
        else:
            self.read_buffer()
            line = self.readline()

        return line

    def readlines(self):
        # type: () -> Iterator[unicode]
        while not self.eof:
            line = self.readline()
            if line:
                yield line

    def read_compressed_chunks(self):
        # type: () -> Iterator[bytes]
        decompressor = zlib.decompressobj()
        while not self.eof:
            self.read_buffer()
            yield decompressor.decompress(self.buffer)
            self.buffer = b''
        yield decompressor.flush()

    def read_compressed_lines(self):
        # type: () -> Iterator[unicode]
        buf = b''
        for chunk in self.read_compressed_chunks():
            buf += chunk
            pos = buf.find(b'\n')
            while pos != -1:
                yield buf[:pos].decode('utf-8')
                buf = buf[pos + 1:]
                pos = buf.find(b'\n')


class InventoryFile(object):
    @classmethod
    def load(cls, stream, uri, joinfunc):
        # type: (IO, unicode, Callable) -> Inventory
        reader = InventoryFileReader(stream)
        line = reader.readline().rstrip()
        if line == '# Sphinx inventory version 1':
            return cls.load_v1(reader, uri, joinfunc)
        elif line == '# Sphinx inventory version 2':
            return cls.load_v2(reader, uri, joinfunc)
        else:
            raise ValueError('invalid inventory header: %s' % line)

    @classmethod
    def load_v1(cls, stream, uri, join):
        # type: (InventoryFileReader, unicode, Callable) -> Inventory
        invdata = {}  # type: Inventory
        projname = stream.readline().rstrip()[11:]
        version = stream.readline().rstrip()[11:]
        for line in stream.readlines():
            name, type, location = line.rstrip().split(None, 2)
            location = join(uri, location)
            # version 1 did not add anchors to the location
            if type == 'mod':
                type = 'py:module'
                location += '#module-' + name
            else:
                type = 'py:' + type
                location += '#' + name
            invdata.setdefault(type, {})[name] = (projname, version, location, '-')
        return invdata

    @classmethod
    def load_v2(cls, stream, uri, join):
        # type: (InventoryFileReader, unicode, Callable) -> Inventory
        invdata = {}  # type: Inventory
        projname = stream.readline().rstrip()[11:]
        version = stream.readline().rstrip()[11:]
        line = stream.readline()
        if 'zlib' not in line:
            raise ValueError('invalid inventory header (not compressed): %s' % line)

        for line in stream.read_compressed_lines():
            # be careful to handle names with embedded spaces correctly
            m = re.match(r'(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)',
                         line.rstrip())
            if not m:
                continue
            name, type, prio, location, dispname = m.groups()
            if type == 'py:module' and type in invdata and name in invdata[type]:
                # due to a bug in 1.1 and below,
                # two inventory entries are created
                # for Python modules, and the first
                # one is correct
                continue
            if location.endswith(u'$'):
                location = location[:-1] + name
            location = join(uri, location)
            invdata.setdefault(type, {})[name] = (projname, version,
                                                  location, dispname)
        return invdata

    @classmethod
    def dump(cls, filename, env, builder):
        # type: (unicode, BuildEnvironment, Builder) -> None
        def escape(string):
            # type: (unicode) -> unicode
            return re.sub("\\s+", " ", string)

        with open(os.path.join(filename), 'wb') as f:
            # header
            f.write((u'# Sphinx inventory version 2\n'
                     u'# Project: %s\n'
                     u'# Version: %s\n'
                     u'# The remainder of this file is compressed using zlib.\n' %
                     (escape(env.config.project),
                      escape(env.config.version))).encode('utf-8'))

            # body
            compressor = zlib.compressobj(9)
            for domainname, domain in sorted(env.domains.items()):
                for name, dispname, typ, docname, anchor, prio in \
                        sorted(domain.get_objects()):
                    if anchor.endswith(name):
                        # this can shorten the inventory by as much as 25%
                        anchor = anchor[:-len(name)] + '$'
                    uri = builder.get_target_uri(docname)
                    if anchor:
                        uri += '#' + anchor
                    if dispname == name:
                        dispname = u'-'
                    entry = (u'%s %s:%s %s %s %s\n' %
                             (name, domainname, typ, prio, uri, dispname))
                    f.write(compressor.compress(entry.encode('utf-8')))
            f.write(compressor.flush())

"""
Based on "python-archive" -- http://pypi.python.org/pypi/python-archive/

Copyright (c) 2010 Gary Wilson Jr. <gary.wilson@gmail.com> and contributers.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
import os
import shutil
import sys
import tarfile
import zipfile


class ArchiveException(Exception):
    """
    Base exception class for all archive errors.
    """


class UnrecognizedArchiveFormat(ArchiveException):
    """
    Error raised when passed file is not a recognized archive format.
    """


def extract(path, to_path=''):
    """
    Unpack the tar or zip file at the specified path to the directory
    specified by to_path.
    """
    Archive(path).extract(to_path)


class Archive(object):
    """
    The external API class that encapsulates an archive implementation.
    """
    def __init__(self, file):
        self._archive = self._archive_cls(file)(file)

    @staticmethod
    def _archive_cls(file):
        cls = None
        if isinstance(file, basestring):
            filename = file
        else:
            try:
                filename = file.name
            except AttributeError:
                raise UnrecognizedArchiveFormat(
                    "File object not a recognized archive format.")
        base, tail_ext = os.path.splitext(filename.lower())
        cls = extension_map.get(tail_ext)
        if not cls:
            base, ext = os.path.splitext(base)
            cls = extension_map.get(ext)
        if not cls:
            raise UnrecognizedArchiveFormat(
                "Path not a recognized archive format: %s" % filename)
        return cls

    def extract(self, to_path=''):
        self._archive.extract(to_path)

    def list(self):
        self._archive.list()


class BaseArchive(object):
    """
    Base Archive class.  Implementations should inherit this class.
    """
    def split_leading_dir(self, path):
        path = str(path)
        path = path.lstrip('/').lstrip('\\')
        if '/' in path and (('\\' in path and path.find('/') < path.find('\\'))
                            or '\\' not in path):
            return path.split('/', 1)
        elif '\\' in path:
            return path.split('\\', 1)
        else:
            return path, ''

    def has_leading_dir(self, paths):
        """
        Returns true if all the paths have the same leading path name
        (i.e., everything is in one subdirectory in an archive)
        """
        common_prefix = None
        for path in paths:
            prefix, rest = self.split_leading_dir(path)
            if not prefix:
                return False
            elif common_prefix is None:
                common_prefix = prefix
            elif prefix != common_prefix:
                return False
        return True

    def extract(self):
        raise NotImplementedError

    def list(self):
        raise NotImplementedError


class TarArchive(BaseArchive):

    def __init__(self, file):
        self._archive = tarfile.open(file)

    def list(self, *args, **kwargs):
        self._archive.list(*args, **kwargs)

    def extract(self, to_path):
        # note: python<=2.5 doesnt seem to know about pax headers, filter them
        members = [member for member in self._archive.getmembers()
                   if member.name != 'pax_global_header']
        leading = self.has_leading_dir(members)
        for member in members:
            name = member.name
            if leading:
                name = self.split_leading_dir(name)[1]
            filename = os.path.join(to_path, name)
            if member.isdir():
                if filename and not os.path.exists(filename):
                    os.makedirs(filename)
            else:
                try:
                    extracted = self._archive.extractfile(member)
                except (KeyError, AttributeError):
                    # Some corrupt tar files seem to produce this
                    # (specifically bad symlinks)
                    print ("In the tar file %s the member %s is invalid: %s" %
                           (name, member.name, sys.exc_info()[1]))
                else:
                    dirname = os.path.dirname(filename)
                    if dirname and not os.path.exists(dirname):
                        os.makedirs(dirname)
                    with open(filename, 'wb') as outfile:
                        shutil.copyfileobj(extracted, outfile)
                finally:
                    if extracted:
                        extracted.close()


class ZipArchive(BaseArchive):

    def __init__(self, file):
        self._archive = zipfile.ZipFile(file)

    def list(self, *args, **kwargs):
        self._archive.printdir(*args, **kwargs)

    def extract(self, to_path):
        namelist = self._archive.namelist()
        leading = self.has_leading_dir(namelist)
        for name in namelist:
            data = self._archive.read(name)
            if leading:
                name = self.split_leading_dir(name)[1]
            filename = os.path.join(to_path, name)
            dirname = os.path.dirname(filename)
            if dirname and not os.path.exists(dirname):
                os.makedirs(dirname)
            if filename.endswith(('/', '\\')):
                # A directory
                if not os.path.exists(filename):
                    os.makedirs(filename)
            else:
                with open(filename, 'wb') as outfile:
                    outfile.write(data)

extension_map = {
    '.tar': TarArchive,
    '.tar.bz2': TarArchive,
    '.tar.gz': TarArchive,
    '.tgz': TarArchive,
    '.tz2': TarArchive,
    '.zip': ZipArchive,
}

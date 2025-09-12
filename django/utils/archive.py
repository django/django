"""
Based on "python-archive" -- https://pypi.org/project/python-archive/

Copyright (c) 2010 Gary Wilson Jr. <gary.wilson@gmail.com> and contributors.

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
import stat
import tarfile
import zipfile

from django.core.exceptions import SuspiciousOperation


class ArchiveException(Exception):
    """
    Base exception class for all archive errors.
    """


class UnrecognizedArchiveFormat(ArchiveException):
    """
    Error raised when passed file is not a recognized archive format.
    """


def extract(path, to_path):
    """
    Unpack the tar or zip file at the specified path to the directory
    specified by to_path.
    """
    with Archive(path) as archive:
        archive.extract(to_path)


class Archive:
    """
    The external API class that encapsulates an archive implementation.
    """

    def __init__(self, file):
        self._archive = self._archive_cls(file)(file)

    @staticmethod
    def _archive_cls(file):
        cls = None
        if isinstance(file, str):
            filename = file
        else:
            try:
                filename = file.name
            except AttributeError:
                raise UnrecognizedArchiveFormat(
                    "File object not a recognized archive format."
                )
        base, tail_ext = os.path.splitext(filename.lower())
        cls = extension_map.get(tail_ext)
        if not cls:
            base, ext = os.path.splitext(base)
            cls = extension_map.get(ext)
        if not cls:
            raise UnrecognizedArchiveFormat(
                "Path not a recognized archive format: %s" % filename
            )
        return cls

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def extract(self, to_path):
        self._archive.extract(to_path)

    def list(self):
        self._archive.list()

    def close(self):
        self._archive.close()


class BaseArchive:
    """
    Base Archive class. Implementations should inherit this class.
    """

    @staticmethod
    def _copy_permissions(mode, filename):
        """
        If the file in the archive has some permissions (this assumes a file
        won't be writable/executable without being readable), apply those
        permissions to the unarchived file.
        """
        if mode & stat.S_IROTH:
            os.chmod(filename, mode)

    def split_leading_dir(self, path):
        path = str(path)
        path = path.lstrip("/").lstrip("\\")
        if "/" in path and (
            ("\\" in path and path.find("/") < path.find("\\")) or "\\" not in path
        ):
            return path.split("/", 1)
        elif "\\" in path:
            return path.split("\\", 1)
        else:
            return path, ""

    def has_leading_dir(self, paths):
        """
        Return True if all the paths have the same leading path name
        (i.e., everything is in one subdirectory in an archive).
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

    def target_filename(self, to_path, name):
        target_path = os.path.abspath(to_path)
        filename = os.path.abspath(os.path.join(target_path, name))
        if not filename.startswith(target_path):
            raise SuspiciousOperation("Archive contains invalid path: '%s'" % name)
        return filename

    def extract(self):
        raise NotImplementedError(
            "subclasses of BaseArchive must provide an extract() method"
        )

    def list(self):
        raise NotImplementedError(
            "subclasses of BaseArchive must provide a list() method"
        )


class TarArchive(BaseArchive):
    def __init__(self, file):
        self._archive = tarfile.open(file)

    def list(self, *args, **kwargs):
        self._archive.list(*args, **kwargs)

    def extract(self, to_path):
        members = self._archive.getmembers()
        leading = self.has_leading_dir(x.name for x in members)
        for member in members:
            name = member.name
            if leading:
                name = self.split_leading_dir(name)[1]
            filename = self.target_filename(to_path, name)
            if member.isdir():
                if filename:
                    os.makedirs(filename, exist_ok=True)
            else:
                try:
                    extracted = self._archive.extractfile(member)
                except (KeyError, AttributeError) as exc:
                    # Some corrupt tar files seem to produce this
                    # (specifically bad symlinks)
                    print(
                        "In the tar file %s the member %s is invalid: %s"
                        % (name, member.name, exc)
                    )
                else:
                    dirname = os.path.dirname(filename)
                    if dirname:
                        os.makedirs(dirname, exist_ok=True)
                    with open(filename, "wb") as outfile:
                        shutil.copyfileobj(extracted, outfile)
                        self._copy_permissions(member.mode, filename)
                finally:
                    if extracted:
                        extracted.close()

    def close(self):
        self._archive.close()


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
            info = self._archive.getinfo(name)
            if leading:
                name = self.split_leading_dir(name)[1]
            if not name:
                continue
            filename = self.target_filename(to_path, name)
            if name.endswith(("/", "\\")):
                # A directory
                os.makedirs(filename, exist_ok=True)
            else:
                dirname = os.path.dirname(filename)
                if dirname:
                    os.makedirs(dirname, exist_ok=True)
                with open(filename, "wb") as outfile:
                    outfile.write(data)
                # Convert ZipInfo.external_attr to mode
                mode = info.external_attr >> 16
                self._copy_permissions(mode, filename)

    def close(self):
        self._archive.close()


extension_map = dict.fromkeys(
    (
        ".tar",
        ".tar.bz2",
        ".tbz2",
        ".tbz",
        ".tz2",
        ".tar.gz",
        ".tgz",
        ".taz",
        ".tar.lzma",
        ".tlz",
        ".tar.xz",
        ".txz",
    ),
    TarArchive,
)
extension_map[".zip"] = ZipArchive

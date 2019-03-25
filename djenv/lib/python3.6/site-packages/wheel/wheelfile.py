from __future__ import print_function

import csv
import hashlib
import os.path
import re
import time
from collections import OrderedDict
from distutils import log as logger
from zipfile import ZIP_DEFLATED, ZipInfo, ZipFile

from wheel.cli import WheelError
from wheel.util import urlsafe_b64decode, as_unicode, native, urlsafe_b64encode, as_bytes, StringIO

# Non-greedy matching of an optional build number may be too clever (more
# invalid wheel filenames will match). Separate regex for .dist-info?
WHEEL_INFO_RE = re.compile(
    r"""^(?P<namever>(?P<name>.+?)-(?P<ver>.+?))(-(?P<build>\d[^-]*))?
     -(?P<pyver>.+?)-(?P<abi>.+?)-(?P<plat>.+?)\.whl$""",
    re.VERBOSE)


def get_zipinfo_datetime(timestamp=None):
    # Some applications need reproducible .whl files, but they can't do this without forcing
    # the timestamp of the individual ZipInfo objects. See issue #143.
    timestamp = int(os.environ.get('SOURCE_DATE_EPOCH', timestamp or time.time()))
    return time.gmtime(timestamp)[0:6]


class WheelFile(ZipFile):
    """A ZipFile derivative class that also reads SHA-256 hashes from
    .dist-info/RECORD and checks any read files against those.
    """

    _default_algorithm = hashlib.sha256

    def __init__(self, file, mode='r'):
        basename = os.path.basename(file)
        self.parsed_filename = WHEEL_INFO_RE.match(basename)
        if not basename.endswith('.whl') or self.parsed_filename is None:
            raise WheelError("Bad wheel filename {!r}".format(basename))

        ZipFile.__init__(self, file, mode, compression=ZIP_DEFLATED, allowZip64=True)

        self.dist_info_path = '{}.dist-info'.format(self.parsed_filename.group('namever'))
        self.record_path = self.dist_info_path + '/RECORD'
        self._file_hashes = OrderedDict()
        self._file_sizes = {}
        if mode == 'r':
            # Ignore RECORD and any embedded wheel signatures
            self._file_hashes[self.record_path] = None, None
            self._file_hashes[self.record_path + '.jws'] = None, None
            self._file_hashes[self.record_path + '.p7s'] = None, None

            # Fill in the expected hashes by reading them from RECORD
            try:
                record = self.open(self.record_path)
            except KeyError:
                raise WheelError('Missing {} file'.format(self.record_path))

            with record:
                for line in record:
                    line = line.decode('utf-8')
                    path, hash_sum, size = line.rsplit(u',', 2)
                    if hash_sum:
                        algorithm, hash_sum = hash_sum.split(u'=')
                        try:
                            hashlib.new(algorithm)
                        except ValueError:
                            raise WheelError('Unsupported hash algorithm: {}'.format(algorithm))

                        if algorithm.lower() in {'md5', 'sha1'}:
                            raise WheelError(
                                'Weak hash algorithm ({}) is not permitted by PEP 427'
                                .format(algorithm))

                        self._file_hashes[path] = (
                            algorithm, urlsafe_b64decode(hash_sum.encode('ascii')))

    def open(self, name_or_info, mode="r", pwd=None):
        def _update_crc(newdata, eof=None):
            if eof is None:
                eof = ef._eof
                update_crc_orig(newdata)
            else:  # Python 2
                update_crc_orig(newdata, eof)

            running_hash.update(newdata)
            if eof and running_hash.digest() != expected_hash:
                raise WheelError("Hash mismatch for file '{}'".format(native(ef_name)))

        ef = ZipFile.open(self, name_or_info, mode, pwd)
        ef_name = as_unicode(name_or_info.filename if isinstance(name_or_info, ZipInfo)
                             else name_or_info)
        if mode == 'r' and not ef_name.endswith('/'):
            if ef_name not in self._file_hashes:
                raise WheelError("No hash found for file '{}'".format(native(ef_name)))

            algorithm, expected_hash = self._file_hashes[ef_name]
            if expected_hash is not None:
                # Monkey patch the _update_crc method to also check for the hash from RECORD
                running_hash = hashlib.new(algorithm)
                update_crc_orig, ef._update_crc = ef._update_crc, _update_crc

        return ef

    def write_files(self, base_dir):
        logger.info("creating '%s' and adding '%s' to it", self.filename, base_dir)
        deferred = []
        for root, dirnames, filenames in os.walk(base_dir):
            # Sort the directory names so that `os.walk` will walk them in a
            # defined order on the next iteration.
            dirnames.sort()
            for name in sorted(filenames):
                path = os.path.normpath(os.path.join(root, name))
                if os.path.isfile(path):
                    arcname = os.path.relpath(path, base_dir)
                    if arcname == self.record_path:
                        pass
                    elif root.endswith('.dist-info'):
                        deferred.append((path, arcname))
                    else:
                        self.write(path, arcname)

        deferred.sort()
        for path, arcname in deferred:
            self.write(path, arcname)

    def write(self, filename, arcname=None, compress_type=None):
        with open(filename, 'rb') as f:
            st = os.fstat(f.fileno())
            data = f.read()

        zinfo = ZipInfo(arcname or filename, date_time=get_zipinfo_datetime(st.st_mtime))
        zinfo.external_attr = st.st_mode << 16
        zinfo.compress_type = ZIP_DEFLATED
        self.writestr(zinfo, data, compress_type)

    def writestr(self, zinfo_or_arcname, bytes, compress_type=None):
        ZipFile.writestr(self, zinfo_or_arcname, bytes, compress_type)
        fname = (zinfo_or_arcname.filename if isinstance(zinfo_or_arcname, ZipInfo)
                 else zinfo_or_arcname)
        logger.info("adding '%s'", fname)
        if fname != self.record_path:
            hash_ = self._default_algorithm(bytes)
            self._file_hashes[fname] = hash_.name, native(urlsafe_b64encode(hash_.digest()))
            self._file_sizes[fname] = len(bytes)

    def close(self):
        # Write RECORD
        if self.fp is not None and self.mode == 'w' and self._file_hashes:
            data = StringIO()
            writer = csv.writer(data, delimiter=',', quotechar='"', lineterminator='\n')
            writer.writerows((
                (
                    fname,
                    algorithm + "=" + hash_,
                    self._file_sizes[fname]
                )
                for fname, (algorithm, hash_) in self._file_hashes.items()
            ))
            writer.writerow((format(self.record_path), "", ""))
            zinfo = ZipInfo(native(self.record_path), date_time=get_zipinfo_datetime())
            zinfo.compress_type = ZIP_DEFLATED
            zinfo.external_attr = 0o664 << 16
            self.writestr(zinfo, as_bytes(data.getvalue()))

        ZipFile.close(self)

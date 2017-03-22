from __future__ import print_function, division, unicode_literals

import gzip
import os
import re
try:
    from io import BytesIO
except ImportError:
    from cStringIO import StringIO as BytesIO

try:
    import brotli
    brotli_installed = True
except ImportError:
    brotli_installed = False


class Compressor(object):

    # Extensions that it's not worth trying to compress
    SKIP_COMPRESS_EXTENSIONS = (
        # Images
        'jpg', 'jpeg', 'png', 'gif', 'webp',
        # Compressed files
        'zip', 'gz', 'tgz', 'bz2', 'tbz',
        # Flash
        'swf', 'flv',
        # Fonts
        'woff', 'woff2')

    def __init__(self, extensions=None, use_gzip=True, use_brotli=True,
                 log=print, quiet=False):
        if extensions is None:
            extensions = self.SKIP_COMPRESS_EXTENSIONS
        self.extension_re = self.get_extension_re(extensions)
        self.use_gzip = use_gzip
        self.use_brotli = use_brotli and brotli_installed
        if not quiet:
            self.log = log

    @staticmethod
    def get_extension_re(extensions):
        if not extensions:
            return re.compile('^$')
        else:
            return re.compile(
                r'\.({0})$'.format('|'.join(map(re.escape, extensions))),
                re.IGNORECASE)

    def should_compress(self, filename):
        return not self.extension_re.search(filename)

    def log(self, message):
        pass

    def compress(self, path):
        with open(path, 'rb') as f:
            data = f.read()
        size = len(data)
        if self.use_brotli:
            compressed = self.compress_brotli(data)
            success = self.write_data(compressed, size, path, '.br', 'Brotli')
            # If Brotli compression wasn't effective gzip won't be either
            if not success:
                return
        if self.use_gzip:
            compressed = self.compress_gzip(data)
            self.write_data(compressed, size, path, '.gz', 'Gzip')

    @staticmethod
    def compress_gzip(data):
        output = BytesIO()
        # Explicitly set mtime to 0 so gzip content is fully determined
        # by file content (0 = "no timestamp" according to gzip spec)
        with gzip.GzipFile(filename='', mode='wb', fileobj=output,
                           compresslevel=9, mtime=0) as gz_file:
            gz_file.write(data)
        return output.getvalue()

    @staticmethod
    def compress_brotli(data):
        return brotli.compress(data)

    def write_data(self, data, orig_size, path, suffix, compression):
        compressed_size = len(data)
        if not self.compressed_effectively(orig_size, compressed_size):
            self.log('Skipping {0} ({1} compression not effective)'.format(
                     path, compression))
            return False
        else:
            self.log('{0} compressed {1} ({2}K -> {3}K)'.format(
                    compression, path, orig_size // 1024,
                    compressed_size // 1024))
            with open(path + suffix, 'wb') as f:
                f.write(data)
            return True

    @staticmethod
    def compressed_effectively(orig_size, compressed_size):
        if orig_size == 0:
            return False
        ratio = compressed_size / orig_size
        return ratio <= 0.95


def main(root, **kwargs):
    compressor = Compressor(**kwargs)
    for dirpath, dirs, files in os.walk(root):
        for filename in files:
            if compressor.should_compress(filename):
                path = os.path.join(dirpath, filename)
                compressor.compress(path)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
            description="Search for all files inside <root> *not* matching "
                        "<extensions> and produce compressed versions with "
                        "'.gz' and '.br' suffixes (as long as this results in a "
                        "smaller file)")
    parser.add_argument('-q', '--quiet', help="Don't produce log output",
                        action='store_true')
    parser.add_argument('--no-gzip', help="Don't produce gzip '.gz' files",
                        action='store_false', dest='use_gzip')
    parser.add_argument('--no-brotli', help="Don't produce brotli '.br' files",
                        action='store_false', dest='use_brotli')
    parser.add_argument('root', help='Path root from which to search for files')
    parser.add_argument('extensions',
                        nargs='*',
                        help='File extensions to exclude from compression '
                             '(default: {})'.format(', '.join(
                                 Compressor.SKIP_COMPRESS_EXTENSIONS)),
                        default=Compressor.SKIP_COMPRESS_EXTENSIONS)
    args = parser.parse_args()
    main(**vars(args))

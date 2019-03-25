from __future__ import print_function

import os.path
import re
import sys

from wheel.cli import WheelError
from wheel.wheelfile import WheelFile

DIST_INFO_RE = re.compile(r"^(?P<namever>(?P<name>.+?)-(?P<ver>\d.*?))\.dist-info$")


def pack(directory, dest_dir, build_number):
    """Repack a previously unpacked wheel directory into a new wheel file.

    The .dist-info/WHEEL file must contain one or more tags so that the target
    wheel file name can be determined.

    :param directory: The unpacked wheel directory
    :param dest_dir: Destination directory (defaults to the current directory)
    """
    # Find the .dist-info directory
    dist_info_dirs = [fn for fn in os.listdir(directory)
                      if os.path.isdir(os.path.join(directory, fn)) and DIST_INFO_RE.match(fn)]
    if len(dist_info_dirs) > 1:
        raise WheelError('Multiple .dist-info directories found in {}'.format(directory))
    elif not dist_info_dirs:
        raise WheelError('No .dist-info directories found in {}'.format(directory))

    # Determine the target wheel filename
    dist_info_dir = dist_info_dirs[0]
    name_version = DIST_INFO_RE.match(dist_info_dir).group('namever')

    # Add the build number if specific
    if build_number:
        name_version += '-' + build_number

    # Read the tags from .dist-info/WHEEL
    with open(os.path.join(directory, dist_info_dir, 'WHEEL')) as f:
        tags = [line.split(' ')[1].rstrip() for line in f if line.startswith('Tag: ')]
        if not tags:
            raise WheelError('No tags present in {}/WHEEL; cannot determine target wheel filename'
                             .format(dist_info_dir))

    # Reassemble the tags for the wheel file
    impls = sorted({tag.split('-')[0] for tag in tags})
    abivers = sorted({tag.split('-')[1] for tag in tags})
    platforms = sorted({tag.split('-')[2] for tag in tags})
    tagline = '-'.join(['.'.join(impls), '.'.join(abivers), '.'.join(platforms)])

    # Repack the wheel
    wheel_path = os.path.join(dest_dir, '{}-{}.whl'.format(name_version, tagline))
    with WheelFile(wheel_path, 'w') as wf:
        print("Repacking wheel as {}...".format(wheel_path), end='')
        sys.stdout.flush()
        wf.write_files(directory)

    print('OK')

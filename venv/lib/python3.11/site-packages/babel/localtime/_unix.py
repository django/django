import datetime
import os
import re

from babel.localtime._helpers import (
    _get_tzinfo,
    _get_tzinfo_from_file,
    _get_tzinfo_or_raise,
)


def _tz_from_env(tzenv: str) -> datetime.tzinfo:
    if tzenv[0] == ':':
        tzenv = tzenv[1:]

    # TZ specifies a file
    if os.path.exists(tzenv):
        return _get_tzinfo_from_file(tzenv)

    # TZ specifies a zoneinfo zone.
    return _get_tzinfo_or_raise(tzenv)


def _get_localzone(_root: str = '/') -> datetime.tzinfo:
    """Tries to find the local timezone configuration.
    This method prefers finding the timezone name and passing that to
    zoneinfo or pytz, over passing in the localtime file, as in the later
    case the zoneinfo name is unknown.
    The parameter _root makes the function look for files like /etc/localtime
    beneath the _root directory. This is primarily used by the tests.
    In normal usage you call the function without parameters.
    """

    tzenv = os.environ.get('TZ')
    if tzenv:
        return _tz_from_env(tzenv)

    # This is actually a pretty reliable way to test for the local time
    # zone on operating systems like OS X.  On OS X especially this is the
    # only one that actually works.
    try:
        link_dst = os.readlink('/etc/localtime')
    except OSError:
        pass
    else:
        pos = link_dst.find('/zoneinfo/')
        if pos >= 0:
            zone_name = link_dst[pos + 10:]
            tzinfo = _get_tzinfo(zone_name)
            if tzinfo is not None:
                return tzinfo

    # Now look for distribution specific configuration files
    # that contain the timezone name.
    tzpath = os.path.join(_root, 'etc/timezone')
    if os.path.exists(tzpath):
        with open(tzpath, 'rb') as tzfile:
            data = tzfile.read()

            # Issue #3 in tzlocal was that /etc/timezone was a zoneinfo file.
            # That's a misconfiguration, but we need to handle it gracefully:
            if data[:5] != b'TZif2':
                etctz = data.strip().decode()
                # Get rid of host definitions and comments:
                if ' ' in etctz:
                    etctz, dummy = etctz.split(' ', 1)
                if '#' in etctz:
                    etctz, dummy = etctz.split('#', 1)

                return _get_tzinfo_or_raise(etctz.replace(' ', '_'))

    # CentOS has a ZONE setting in /etc/sysconfig/clock,
    # OpenSUSE has a TIMEZONE setting in /etc/sysconfig/clock and
    # Gentoo has a TIMEZONE setting in /etc/conf.d/clock
    # We look through these files for a timezone:
    timezone_re = re.compile(r'\s*(TIME)?ZONE\s*=\s*"(?P<etctz>.+)"')

    for filename in ('etc/sysconfig/clock', 'etc/conf.d/clock'):
        tzpath = os.path.join(_root, filename)
        if not os.path.exists(tzpath):
            continue
        with open(tzpath) as tzfile:
            for line in tzfile:
                match = timezone_re.match(line)
                if match is not None:
                    # We found a timezone
                    etctz = match.group("etctz")
                    return _get_tzinfo_or_raise(etctz.replace(' ', '_'))

    # No explicit setting existed. Use localtime
    for filename in ('etc/localtime', 'usr/local/etc/localtime'):
        tzpath = os.path.join(_root, filename)

        if not os.path.exists(tzpath):
            continue
        return _get_tzinfo_from_file(tzpath)

    raise LookupError('Can not find any timezone configuration')

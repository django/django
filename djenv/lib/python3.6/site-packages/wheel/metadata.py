"""
Tools for converting old- to new-style metadata.
"""

import os.path
import re
import textwrap

import pkg_resources

from .pkginfo import read_pkg_info

# Wheel itself is probably the only program that uses non-extras markers
# in METADATA/PKG-INFO. Support its syntax with the extra at the end only.
EXTRA_RE = re.compile(
    r"""^(?P<package>.*?)(;\s*(?P<condition>.*?)(extra == '(?P<extra>.*?)')?)$""")


def requires_to_requires_dist(requirement):
    """Return the version specifier for a requirement in PEP 345/566 fashion."""
    if getattr(requirement, 'url', None):
        return " @ " + requirement.url

    requires_dist = []
    for op, ver in requirement.specs:
        requires_dist.append(op + ver)
    if not requires_dist:
        return ''
    return " (%s)" % ','.join(sorted(requires_dist))


def convert_requirements(requirements):
    """Yield Requires-Dist: strings for parsed requirements strings."""
    for req in requirements:
        parsed_requirement = pkg_resources.Requirement.parse(req)
        spec = requires_to_requires_dist(parsed_requirement)
        extras = ",".join(sorted(parsed_requirement.extras))
        if extras:
            extras = "[%s]" % extras
        yield (parsed_requirement.project_name + extras + spec)


def generate_requirements(extras_require):
    """
    Convert requirements from a setup()-style dictionary to ('Requires-Dist', 'requirement')
    and ('Provides-Extra', 'extra') tuples.

    extras_require is a dictionary of {extra: [requirements]} as passed to setup(),
    using the empty extra {'': [requirements]} to hold install_requires.
    """
    for extra, depends in extras_require.items():
        condition = ''
        extra = extra or ''
        if ':' in extra:  # setuptools extra:condition syntax
            extra, condition = extra.split(':', 1)

        extra = pkg_resources.safe_extra(extra)
        if extra:
            yield 'Provides-Extra', extra
            if condition:
                condition = "(" + condition + ") and "
            condition += "extra == '%s'" % extra

        if condition:
            condition = ' ; ' + condition

        for new_req in convert_requirements(depends):
            yield 'Requires-Dist', new_req + condition


def pkginfo_to_metadata(egg_info_path, pkginfo_path):
    """
    Convert .egg-info directory with PKG-INFO to the Metadata 2.1 format
    """
    pkg_info = read_pkg_info(pkginfo_path)
    pkg_info.replace_header('Metadata-Version', '2.1')
    # Those will be regenerated from `requires.txt`.
    del pkg_info['Provides-Extra']
    del pkg_info['Requires-Dist']
    requires_path = os.path.join(egg_info_path, 'requires.txt')
    if os.path.exists(requires_path):
        with open(requires_path) as requires_file:
            requires = requires_file.read()

        parsed_requirements = sorted(pkg_resources.split_sections(requires),
                                     key=lambda x: x[0] or '')
        for extra, reqs in parsed_requirements:
            for key, value in generate_requirements({extra: reqs}):
                if (key, value) not in pkg_info.items():
                    pkg_info[key] = value

    description = pkg_info['Description']
    if description:
        pkg_info.set_payload(dedent_description(pkg_info))
        del pkg_info['Description']

    return pkg_info


def pkginfo_unicode(pkg_info, field):
    """Hack to coax Unicode out of an email Message() - Python 3.3+"""
    text = pkg_info[field]
    field = field.lower()
    if not isinstance(text, str):
        if not hasattr(pkg_info, 'raw_items'):  # Python 3.2
            return str(text)
        for item in pkg_info.raw_items():
            if item[0].lower() == field:
                text = item[1].encode('ascii', 'surrogateescape') \
                    .decode('utf-8')
                break

    return text


def dedent_description(pkg_info):
    """
    Dedent and convert pkg_info['Description'] to Unicode.
    """
    description = pkg_info['Description']

    # Python 3 Unicode handling, sorta.
    surrogates = False
    if not isinstance(description, str):
        surrogates = True
        description = pkginfo_unicode(pkg_info, 'Description')

    description_lines = description.splitlines()
    description_dedent = '\n'.join(
        # if the first line of long_description is blank,
        # the first line here will be indented.
        (description_lines[0].lstrip(),
         textwrap.dedent('\n'.join(description_lines[1:])),
         '\n'))

    if surrogates:
        description_dedent = description_dedent \
            .encode("utf8") \
            .decode("ascii", "surrogateescape")

    return description_dedent

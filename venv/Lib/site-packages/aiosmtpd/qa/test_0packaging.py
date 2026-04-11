# Copyright 2014-2021 The aiosmtpd Developers
# SPDX-License-Identifier: Apache-2.0

"""Test meta / packaging"""

import re
import subprocess
from datetime import datetime
from itertools import tee
from pathlib import Path

import pytest

# noinspection PyPackageRequirements
from packaging import version

from aiosmtpd import __version__

RE_DUNDERVER = re.compile(r"__version__\s*?=\s*?(['\"])(?P<ver>[^'\"]+)\1\s*$")
RE_VERHEADING = re.compile(r"(?P<ver>([0-9.]+)\S*)\s*\((?P<date>[^)]+)\)")


@pytest.fixture
def aiosmtpd_version() -> version.Version:
    return version.parse(__version__)


class TestVersion:
    def test_pep440(self, aiosmtpd_version: version.Version):
        """Ensure version number compliance to PEP-440"""
        assert isinstance(
            aiosmtpd_version, version.Version
        ), "Version number must comply with PEP-440"

    # noinspection PyUnboundLocalVariable
    def test_ge_master(
        self, aiosmtpd_version: version.Version, capsys: pytest.CaptureFixture
    ):
        """Ensure version is monotonically increasing"""
        reference = "master:aiosmtpd/__init__.py"
        cmd = f"git show {reference}".split()
        try:
            with capsys.disabled():
                master_smtp = subprocess.check_output(cmd).decode()  # nosec
        except subprocess.CalledProcessError:
            pytest.skip("Skipping due to git error")

        try:
            m = next(m for ln in master_smtp.splitlines() if (m := RE_DUNDERVER.match(ln)))
        except StopIteration:
            pytest.fail(f"Cannot find __version__ in {reference}!")
        master_ver = version.parse(m.group("ver"))
        assert aiosmtpd_version >= master_ver, "Version number cannot be < master's"


class TestNews:
    news_rst = list(Path(__file__).parent.parent.rglob("*/NEWS.rst"))[0]

    def test_NEWS_version(self, aiosmtpd_version: version.Version):
        with self.news_rst.open("rt") as fin:
            # pairwise() from https://docs.python.org/3/library/itertools.html
            a, b = tee(fin)
            next(b, None)
            for ln1, ln2 in zip(a, b):
                if not ln1[0].isdigit():
                    continue
                ln1 = ln1.strip()
                ln2 = ln2.strip()
                equals = "=" * len(ln1)
                if not ln2.startswith(equals):
                    continue
                break
        newsvers = ln1.split()[0]
        newsver = version.parse(newsvers)
        if newsver.base_version < aiosmtpd_version.base_version:
            pytest.fail(
                f"NEWS.rst is not updated: "
                f"{newsver.base_version} < {aiosmtpd_version.base_version}"
            )

    def test_release_date(self, aiosmtpd_version: version.Version):
        if aiosmtpd_version.pre is not None:
            pytest.skip("Not a release version")
        with self.news_rst.open("rt") as fin:
            for ln in fin:
                ln = ln.strip()
                m = RE_VERHEADING.match(ln)
                if not m:
                    continue
                ver = version.Version(m.group("ver"))
                if ver != aiosmtpd_version:
                    continue
                try:
                    datetime.strptime(m.group("date"), "%Y-%m-%d")
                except ValueError:
                    pytest.fail("Release version not dated correctly")
                break
            else:
                pytest.fail("Release version has no NEWS fragment")

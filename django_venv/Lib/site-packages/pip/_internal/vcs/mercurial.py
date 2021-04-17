from __future__ import absolute_import

import logging
import os

from pip._vendor.six.moves import configparser

from pip._internal.utils.misc import display_path, path_to_url
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.vcs.versioncontrol import VersionControl, vcs

logger = logging.getLogger(__name__)


class Mercurial(VersionControl):
    name = 'hg'
    dirname = '.hg'
    repo_name = 'clone'
    schemes = ('hg', 'hg+http', 'hg+https', 'hg+ssh', 'hg+static-http')

    @staticmethod
    def get_base_rev_args(rev):
        return [rev]

    def export(self, location, url):
        """Export the Hg repository at the url to the destination location"""
        with TempDirectory(kind="export") as temp_dir:
            self.unpack(temp_dir.path, url=url)

            self.run_command(
                ['archive', location], show_stdout=False, cwd=temp_dir.path
            )

    def fetch_new(self, dest, url, rev_options):
        rev_display = rev_options.to_display()
        logger.info(
            'Cloning hg %s%s to %s',
            url,
            rev_display,
            display_path(dest),
        )
        self.run_command(['clone', '--noupdate', '-q', url, dest])
        cmd_args = ['update', '-q'] + rev_options.to_args()
        self.run_command(cmd_args, cwd=dest)

    def switch(self, dest, url, rev_options):
        repo_config = os.path.join(dest, self.dirname, 'hgrc')
        config = configparser.RawConfigParser()
        try:
            config.read(repo_config)
            config.set('paths', 'default', url)
            with open(repo_config, 'w') as config_file:
                config.write(config_file)
        except (OSError, configparser.NoSectionError) as exc:
            logger.warning(
                'Could not switch Mercurial repository to %s: %s', url, exc,
            )
        else:
            cmd_args = ['update', '-q'] + rev_options.to_args()
            self.run_command(cmd_args, cwd=dest)

    def update(self, dest, url, rev_options):
        self.run_command(['pull', '-q'], cwd=dest)
        cmd_args = ['update', '-q'] + rev_options.to_args()
        self.run_command(cmd_args, cwd=dest)

    @classmethod
    def get_remote_url(cls, location):
        url = cls.run_command(
            ['showconfig', 'paths.default'],
            show_stdout=False, cwd=location).strip()
        if cls._is_local_repository(url):
            url = path_to_url(url)
        return url.strip()

    @classmethod
    def get_revision(cls, location):
        """
        Return the repository-local changeset revision number, as an integer.
        """
        current_revision = cls.run_command(
            ['parents', '--template={rev}'],
            show_stdout=False, cwd=location).strip()
        return current_revision

    @classmethod
    def get_requirement_revision(cls, location):
        """
        Return the changeset identification hash, as a 40-character
        hexadecimal string
        """
        current_rev_hash = cls.run_command(
            ['parents', '--template={node}'],
            show_stdout=False, cwd=location).strip()
        return current_rev_hash

    @classmethod
    def is_commit_id_equal(cls, dest, name):
        """Always assume the versions don't match"""
        return False


vcs.register(Mercurial)

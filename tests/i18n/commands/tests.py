import os
import re
from subprocess import Popen, PIPE

from django.core.management.utils import find_command

can_run_extraction_tests = False
can_run_compilation_tests = False

# checks if it can find xgettext on the PATH and
# imports the extraction tests if yes
xgettext_cmd = find_command('xgettext')
if xgettext_cmd:
    p = Popen('%s --version' % xgettext_cmd, shell=True, stdout=PIPE, stderr=PIPE, close_fds=os.name != 'nt', universal_newlines=True)
    output = p.communicate()[0]
    match = re.search(r'(?P<major>\d+)\.(?P<minor>\d+)', output)
    if match:
        xversion = (int(match.group('major')), int(match.group('minor')))
        if xversion >= (0, 15):
            can_run_extraction_tests = True
    del p

if find_command('msgfmt'):
    can_run_compilation_tests = True

import os
import re
from subprocess import Popen, PIPE

can_run_extraction_tests = False
can_run_compilation_tests = False

def find_command(cmd, path=None, pathext=None):
    if path is None:
        path = os.environ.get('PATH', []).split(os.pathsep)
    if isinstance(path, basestring):
        path = [path]
    # check if there are funny path extensions for executables, e.g. Windows
    if pathext is None:
        pathext = os.environ.get('PATHEXT', '.COM;.EXE;.BAT;.CMD').split(os.pathsep)
    # don't use extensions if the command ends with one of them
    for ext in pathext:
        if cmd.endswith(ext):
            pathext = ['']
            break
    # check if we find the command on PATH
    for p in path:
        f = os.path.join(p, cmd)
        if os.path.isfile(f):
            return f
        for ext in pathext:
            fext = f + ext
            if os.path.isfile(fext):
                return fext
    return None

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

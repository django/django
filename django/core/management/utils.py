import os
from subprocess import PIPE, Popen


def popen_wrapper(args):
    """
    Friendly wrapper around Popen.

    Returns stdout output, stderr output and OS status code.
    """
    p = Popen(args, shell=False, stdout=PIPE, stderr=PIPE,
              close_fds=os.name != 'nt', universal_newlines=True)
    output, errors = p.communicate()
    return output, errors, p.returncode

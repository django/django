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

def handle_extensions(extensions=('html',), ignored=('py',)):
    """
    Organizes multiple extensions that are separated with commas or passed by
    using --extension/-e multiple times. Note that the .py extension is ignored
    here because of the way non-*.py files are handled in make_messages() (they
    are copied to file.ext.py files to trick xgettext to parse them as Python
    files).

    For example: running 'django-admin makemessages -e js,txt -e xhtml -a'
    would result in an extension list: ['.js', '.txt', '.xhtml']

    >>> handle_extensions(['.html', 'html,js,py,py,py,.py', 'py,.py'])
    set(['.html', '.js'])
    >>> handle_extensions(['.html, txt,.tpl'])
    set(['.html', '.tpl', '.txt'])
    """
    ext_list = []
    for ext in extensions:
        ext_list.extend(ext.replace(' ', '').split(','))
    for i, ext in enumerate(ext_list):
        if not ext.startswith('.'):
            ext_list[i] = '.%s' % ext_list[i]
    return set([x for x in ext_list if x.strip('.') not in ignored])

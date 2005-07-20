#!/usr/bin/env python
from django.core import management
import os, sys

ACTION_MAPPING = {
    'adminindex': management.get_admin_index,
#     'dbcheck': management.database_check,
    'runserver': management.runserver,
    'sql': management.get_sql_create,
    'sqlall': management.get_sql_all,
    'sqlclear': management.get_sql_delete,
    'sqlindexes': management.get_sql_indexes,
    'sqlinitialdata': management.get_sql_initial_data,
    'sqlreset': management.get_sql_reset,
    'sqlsequencereset': management.get_sql_sequence_reset,
    'startapp': management.startapp,
    'startproject': management.startproject,
    'init': management.init,
    'install': management.install,
}

def usage():
    sys.stderr.write("Usage: %s [action]\n" % sys.argv[0])
    available_actions = ACTION_MAPPING.keys()
    available_actions.sort()
    sys.stderr.write("Available actions:\n")
    for a in available_actions:
        func = ACTION_MAPPING[a]
        sys.stderr.write("  %s %s-- %s\n" % (a, func.args, getattr(func, 'help_doc', func.__doc__)))
    sys.exit(1)

if __name__ == "__main__":
    try:
        action = sys.argv[1]
    except IndexError:
        usage()
    if not ACTION_MAPPING.has_key(action):
        usage()
    if action == 'init':
        ACTION_MAPPING[action]()
        sys.exit(0)
    elif action in ('startapp', 'startproject'):
        try:
            name = sys.argv[2]
        except IndexError:
            usage()
        ACTION_MAPPING[action](name, os.getcwd())
        sys.exit(0)
    elif action == 'runserver':
        if len(sys.argv) < 3:
            port = '8000'
        else:
            port = sys.argv[2]
        ACTION_MAPPING[action](port)
    elif action == 'dbcheck':
        from django.core import meta
        mod_list = meta.get_all_installed_modules()
    else:
        from django.core import meta
        try:
            mod_list = [meta.get_app(app_label) for app_label in sys.argv[2:]]
        except ImportError, e:
            sys.stderr.write("Error: %s. Are you sure your INSTALLED_APPS setting is correct?\n" % e)
            sys.exit(1)
        if not mod_list:
            usage()
    if action not in ('adminindex', 'dbcheck', 'install', 'sqlindexes'):
        print "BEGIN;"
    for mod in mod_list:
        output = ACTION_MAPPING[action](mod)
        if output:
            print '\n'.join(output)
    if action not in ('adminindex', 'dbcheck', 'install', 'sqlindexes'):
        print "COMMIT;"

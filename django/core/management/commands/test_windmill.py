from django.core.management.base import BaseCommand
from windmill.authoring import djangotest
import sys, os
from time import sleep
import types
import logging

class ServerContainer(object):
    start_test_server = djangotest.start_test_server
    stop_test_server = djangotest.stop_test_server

def attempt_import(name, suffix):
        try:
            mod = __import__(name+'.'+suffix)
        except ImportError:
            mod = None
        if mod is not None:
            s = name.split('.')
            mod = __import__(s.pop(0))
            for x in s+[suffix]:
                mod = getattr(mod, x)
        return mod

class Command(BaseCommand):

    help = "Run windmill tests. Specify a browser, if one is not passed Firefox will be used"

    args = '<label label ...>'
    label = 'label'

    def handle(self, *labels, **options):

        from windmill.conf import global_settings
        from windmill.authoring.djangotest import WindmillDjangoUnitTest
        if 'ie' in labels:
            global_settings.START_IE = True
            sys.argv.remove('ie')
        elif 'safari' in labels:
            global_settings.START_SAFARI = True
            sys.argv.remove('safari')
        elif 'chrome' in labels:
            global_settings.START_CHROME = True
            sys.argv.remove('chrome')
        else:
            global_settings.START_FIREFOX = True
            if 'firefox' in labels:
                sys.argv.remove('firefox')

        if 'manage.py' in sys.argv:
            sys.argv.remove('manage.py')
        if 'test_windmill' in sys.argv:
            sys.argv.remove('test_windmill')
        server_container = ServerContainer()
        server_container.start_test_server()

        global_settings.TEST_URL = 'http://localhost:%d' % server_container.server_thread.port

        # import windmill
        # windmill.stdout, windmill.stdin = sys.stdout, sys.stdin
        from windmill.authoring import setup_module, teardown_module

        from django.conf import settings
        tests = []
        for name in settings.INSTALLED_APPS:
            for suffix in ['tests', 'wmtests', 'windmilltests']:
                x = attempt_import(name, suffix)
                if x is not None: tests.append((suffix,x,));

        wmtests = []
        for (ttype, mod,) in tests:
            if ttype == 'tests':
                for ucls in [getattr(mod, x) for x in dir(mod)
                             if ( type(getattr(mod, x, None)) in (types.ClassType,
                                                               types.TypeType) ) and
                             issubclass(getattr(mod, x), WindmillDjangoUnitTest)
                             ]:
                    wmtests.append(ucls.test_dir)

            else:
                if mod.__file__.endswith('__init__.py') or mod.__file__.endswith('__init__.pyc'):
                    wmtests.append(os.path.join(*os.path.split(os.path.abspath(mod.__file__))[:-1]))
                else:
                    wmtests.append(os.path.abspath(mod.__file__))

        if len(wmtests) is 0:
            print 'Sorry, no windmill tests found.'
        else:
            testtotals = {}
            x = logging.getLogger()
            x.setLevel(0)
            from windmill.server.proxy import logger
            from functest import bin
            from functest import runner
            runner.CLIRunner.final = classmethod(lambda self, totals: testtotals.update(totals) )
            import windmill
            setup_module(tests[0][1])
            sys.argv = sys.argv + wmtests
            bin.cli()
            teardown_module(tests[0][1])
            if testtotals['fail'] is not 0:
                sleep(.5)
                sys.exit(1)

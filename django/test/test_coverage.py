import coverage, time

import os, sys

from django.conf import settings
from django.db.models.loading import get_app, get_apps

from django.test.simple import DefaultTestRunner as base_run_tests

from django.utils.module_tools import get_all_modules
from django.utils.translation import ugettext as _

def _get_app_package(app_model_module):
    """
    Returns the app module name from the app model module.
    """
    return '.'.join(app_model_module.__name__.split('.')[:-1])


class BaseCoverageRunner(object):
    """
    Placeholder class for coverage runners. Intended to be easily extended.
    """

    def __init__(self):
        """Placeholder (since it is overrideable)"""
        self.cov = coverage.coverage(cover_pylib=True, auto_data=True)
        self.cov.use_cache(True)
        self.cov.load()
        #self.cov.combine()
        


    def run_tests(self, test_labels, verbosity=1, interactive=True,
                  extra_tests=[]):
        """
        Runs the specified tests while generating code coverage statistics. Upon
        the tests' completion, the results are printed to stdout.
        """
        #self.cov.erase()
        #Allow an on-disk cache of coverage stats.
        #self.cov.use_cache(0)
        #for e in getattr(settings, 'COVERAGE_CODE_EXCLUDES', []):
        #    self.cov.exclude(e)


        self.cov.start()
        brt = base_run_tests()
        results = brt.run_tests(test_labels, verbosity, interactive, extra_tests)
        self.cov.stop()
        #self.cov.erase()

        coverage_modules = []
        if test_labels:
            for label in test_labels:
                label = label.split('.')[0]
                app = get_app(label)
                coverage_modules.append(_get_app_package(app))
        else:
            for app in get_apps():
                coverage_modules.append(_get_app_package(app))

        coverage_modules.extend(getattr(settings, 'COVERAGE_ADDITIONAL_MODULES', []))

        packages, self.modules, self.excludes, self.errors = get_all_modules(
            coverage_modules, getattr(settings, 'COVERAGE_MODULE_EXCLUDES', []),
            getattr(settings, 'COVERAGE_PATH_EXCLUDES', []))



        return results

class ConsoleReportCoverageRunner(BaseCoverageRunner):

    def run_tests(self, *args, **kwargs):
        """docstring for run_tests"""
        res = super(ConsoleReportCoverageRunner, self).run_tests( *args, **kwargs)
        self.cov.report(self.modules.values(), show_missing=1)

        if self.excludes:
            print >> sys.stdout
            print >> sys.stdout, _("The following packages or modules were excluded:"),
            for e in self.excludes:
                print >> sys.stdout, e,
            print >>sys.stdout
        if self.errors:
            print >> sys.stdout
            print >> sys.stderr, _("There were problems with the following packages or modules:"),
            for e in self.errors:
                print >> sys.stderr, e,
            print >> sys.stdout
        return res

class ReportingCoverageRunner(BaseCoverageRunner):
    """Runs coverage.py analysis, as well as generating detailed HTML reports."""

    def __init__(self, outdir = None):
        """
        Constructor, overrides BaseCoverageRunner. Sets output directory
        for reports. Parameter or setting.
        """
        super(ReportingCoverageRunner, self).__init__()
        if(outdir):
            self.outdir = outdir
        else:
            # Realistically, we aren't going to ship the entire reporting framework..
            # but for the time being I have left it in.
            self.outdir = getattr(settings, 'COVERAGE_REPORT_HTML_OUTPUT_DIR', 'test_html')
            self.outdir = os.path.abspath(self.outdir)
            # Create directory
            if( not os.path.exists(self.outdir)):
                os.mkdir(self.outdir)


    def run_tests(self, *args, **kwargs):
        """
        Overrides BaseCoverageRunner.run_tests, and adds html report generation
        with the results
        """
        res = super(ReportingCoverageRunner, self).run_tests( *args, **kwargs)
        self.cov.html_report(self.modules.values(),
                                directory=self.outdir,
                                ignore_errors=True,
                                omit_prefixes='modeltests')
        print >>sys.stdout
        print >>sys.stdout, _("HTML reports were output to '%s'") %self.outdir

        return res


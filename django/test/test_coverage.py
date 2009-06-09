import coverage, time
import os, sys

from django.conf import settings
from django.db.models import get_app, get_apps
from django.test.simple import DefaultTestRunner as base_run_tests

from django.utils.module_tools import get_all_modules, find_or_load_module
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
        pass

    def run_tests(self, test_labels, verbosity=1, interactive=True,
                  extra_tests=[]):
        """
        Runs the specified tests while generating code coverage statistics. Upon
        the tests' completion, the results are printed to stdout.
        """
        coverage.erase()
        #Allow an on-disk cache of coverage stats.
        #coverage.use_cache(0)
        for e in getattr(settings, 'COVERAGE_CODE_EXCLUDES', []):
            coverage.exclude(e)

        coverage.start()
        brt = base_run_tests()
        results = brt.run_tests(test_labels, verbosity, interactive, extra_tests)
        coverage.stop()

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
        for mods in self.modules.keys():
            coverage.analysis2(ModuleVars(mods, self.modules[mods]).source_file)
        coverage.report(self.modules.values(), show_missing=1)
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
        coverage._the_coverage.save()
        return results


class ReportingCoverageRunner(BaseCoverageRunner):
    """Runs coverage.py analysis, as well as generating detailed HTML reports."""

    def __init__(self, outdir = None):
        """
        Constructor, overrides BaseCoverageRunner. Sets output directory
        for reports. Parameter or setting.
        """
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
        res = BaseCoverageRunner.run_tests(self, *args, **kwargs)
        coverage._the_coverage.load()
        cov = coverage.html.HtmlReporter(coverage._the_coverage)
        cov.report(self.modules.values(), self.outdir)
        #coverage._the_coverage.html_report(self.modules.values(), self.outdir)
        print >>sys.stdout
        print >>sys.stdout, _("HTML reports were output to '%s'") %self.outdir

        return res


try:
    set
except:
    from sets import Set as set


class ModuleVars(object):
    modules = dict()
    def __new__(cls, module_name, module=None):
        if cls.modules.get(module_name, None):
            return cls.modules.get(module_name)
        else:
            obj=super(ModuleVars, cls).__new__(cls)
            obj._init(module_name, module)
            cls.modules[module_name] = obj
            return obj

    def _init(self, module_name, module):
        source_file, stmts, excluded, missed, missed_display = coverage.analysis2(module)
        executed = list(set(stmts).difference(missed))
        total = list(set(stmts).union(excluded))
        total.sort()
        title = module.__name__
        total_count = len(total)
        executed_count = len(executed)
        excluded_count = len(excluded)
        missed_count = len(missed)
        try:
            percent_covered = float(len(executed))/len(stmts)*100
        except ZeroDivisionError:
            percent_covered = 100
        test_timestamp = time.strftime('%a %Y-%m-%d %H:%M %Z')
        severity = 'normal'
        if percent_covered < 75: severity = 'warning'
        if percent_covered < 50: severity = 'critical'

        for k, v in locals().iteritems():
            setattr(self, k, v)

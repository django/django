#!/usr/bin/env python

# This script aims to help developers locate forms and view code that needs to
# use the new CSRF protection in Django 1.2.  It tries to find all the code that
# may need the steps described in the CSRF documentation.  It does not modify
# any code directly, it merely attempts to locate it.  Developers should be
# aware of its limitations, described below.
#
# For each template that contains at least one POST form, the following info is printed:
#
# <Absolute path to template>
#   AKA: <Aliases (relative to template directory/directories that contain it)>
#   POST forms: <Number of POST forms>
#   With token: <Number of POST forms with the CSRF token already added>
#   Without token:
#     <File name and line number of form without token>
#
#   Searching for:
#     <Template names that need to be searched for in view code
#      (includes templates that 'include' current template)>
#
#   Found:
#     <File name and line number of any view code found>
#
# The format used allows this script to be used in Emacs grep mode:
#   M-x grep
#   Run grep (like this): /path/to/my/virtualenv/python /path/to/django/src/extras/csrf_migration_helper.py --settings=mysettings /path/to/my/srcs


# Limitations
# ===========
#
# - All templates must be stored on disk in '.html' or '.htm' files.
#   (extensions configurable below)
#
# - All Python code must be stored on disk in '.py' files.  (extensions
#   configurable below)
#
# - All templates must be accessible from TEMPLATE_DIRS or from the 'templates/'
#   directory in apps specified in INSTALLED_APPS.  Non-file based template
#   loaders are out of the picture, because there is no way to ask them to
#   return all templates.
#
# - If you put the {% csrf_token %} tag on the same line as the <form> tag it
#   will be detected, otherwise it will be assumed that the form does not have
#   the token.
#
# - It's impossible to programmatically determine which forms should and should
#   not have the token added.  The developer must decide when to do this,
#   ensuring that the token is only added to internally targetted forms.
#
# - It's impossible to programmatically work out when a template is used.  The
#   attempts to trace back to view functions are guesses, and could easily fail
#   in the following ways:
#
#   * If the 'include' template tag is used with a variable
#     i.e. {% include tname %} where tname is a variable containing the actual
#     template name, rather than {% include "my_template.html" %}.
#
#   * If the template name has been built up by view code instead of as a simple
#     string.  For example, generic views and the admin both do this.  (These
#     apps are both contrib and both use RequestContext already, as it happens).
#
#   * If the 'ssl' tag (or any template tag other than 'include') is used to
#     include the template in another template.
#
# - All templates belonging to apps referenced in INSTALLED_APPS will be
#   searched, which may include third party apps or Django contrib.  In some
#   cases, this will be a good thing, because even if the templates of these
#   apps have been fixed by someone else, your own view code may reference the
#   same template and may need to be updated.
#
#   You may, however, wish to comment out some entries in INSTALLED_APPS or
#   TEMPLATE_DIRS before running this script.

# Improvements to this script are welcome!

# Configuration
# =============

TEMPLATE_EXTENSIONS = [
    ".html",
    ".htm",
    ]

PYTHON_SOURCE_EXTENSIONS = [
    ".py",
    ]

TEMPLATE_ENCODING = "UTF-8"

PYTHON_ENCODING = "UTF-8"

# Method
# ======

# Find templates:
#  - template dirs
#  - installed apps
#
# Search for POST forms
#  - Work out what the name of the template is, as it would appear in an
#    'include' or get_template() call. This can be done by comparing template
#    filename to all template dirs.  Some templates can have more than one
#    'name' e.g.  if a directory and one of its child directories are both in
#    TEMPLATE_DIRS.  This is actually a common hack used for
#    overriding-and-extending admin templates.
#
# For each POST form,
# - see if it already contains '{% csrf_token %}' immediately after <form>
# - work back to the view function(s):
#   - First, see if the form is included in any other templates, then
#     recursively compile a list of affected templates.
#   - Find any code function that references that template.  This is just a
#     brute force text search that can easily return false positives
#     and fail to find real instances.


import os
import sys
import re
try:
    set
except NameError:
    from sets import Set as set


USAGE = """
This tool helps to locate forms that need CSRF tokens added and the
corresponding view code.  This processing is NOT fool proof, and you should read
the help contained in the script itself.  Also, this script may need configuring
(by editing the script) before use.

Usage:

python csrf_migration_helper.py [--settings=path.to.your.settings] /path/to/python/code [more paths...]

  Paths can be specified as relative paths.

  With no arguments, this help is printed.
"""

_POST_FORM_RE = \
    re.compile(r'(<form\W[^>]*\bmethod\s*=\s*(\'|"|)POST(\'|"|)\b[^>]*>)', re.IGNORECASE)
_TOKEN_RE = re.compile('\{% csrf_token')

def get_template_dirs():
    """
    Returns a set of all directories that contain project templates.
    """
    from django.conf import settings
    dirs = set()
    if 'django.template.loaders.filesystem.load_template_source' in settings.TEMPLATE_LOADERS:
        dirs.update(map(unicode, settings.TEMPLATE_DIRS))

    if 'django.template.loaders.app_directories.load_template_source' in settings.TEMPLATE_LOADERS:
        from django.template.loaders.app_directories import app_template_dirs
        dirs.update(app_template_dirs)
    return dirs

def make_template_info(filename, root_dirs):
    """
    Creates a Template object for a filename, calculating the possible
    relative_filenames from the supplied filename and root template directories
    """
    return Template(filename,
                    [filename[len(d)+1:] for d in root_dirs if filename.startswith(d)])


class Template(object):
    def __init__(self, absolute_filename, relative_filenames):
        self.absolute_filename, self.relative_filenames = absolute_filename, relative_filenames

    def content(self):
        try:
            return self._content
        except AttributeError:
            fd = open(self.absolute_filename)
            content = fd.read().decode(TEMPLATE_ENCODING)
            fd.close()
            self._content = content
            return content
    content = property(content)

    def post_form_info(self):
        """
        Get information about any POST forms in the template.
        Returns [(linenumber, csrf_token added)]
        """
        matches = []
        for ln, line in enumerate(self.content.split("\n")):
            m = _POST_FORM_RE.search(line)
            if m is not None:
                matches.append((ln + 1, _TOKEN_RE.search(line) is not None))
        return matches

    def includes_template(self, t):
        """
        Returns true if this template includes template 't' (via {% include %})
        """
        for r in t.relative_filenames:
            if re.search(r'\{%\s*include\s+"' + re.escape(r) + r'"\s*%\}', self.content):
                return True
        return False

    def related_templates(self):
        """
        Returns all templates that include this one, recursively.  (starting
        with this one)
        """
        try:
            return self._related_templates
        except AttributeError:
            pass

        retval = set([self])
        for r in self.relative_filenames:
            for t in self.all_templates:
                if t.includes_template(self):
                    # If two templates mutually include each other, directly or
                    # indirectly, we have a problem here...
                    retval = retval.union(t.related_templates())

        self._related_templates = retval
        return retval

    def __repr__(self):
        return repr(self.absolute_filename)

    def __eq__(self, other):
        return self.absolute_filename == other.absolute_filename

    def __hash__(self):
        return hash(self.absolute_filename)

def get_templates(dirs):
    """
    Returns all files in dirs that have template extensions, as Template
    objects.
    """
    templates = set()
    for root in dirs:
        for (dirpath, dirnames, filenames) in os.walk(root):
            for f in filenames:
                if len([True for e in TEMPLATE_EXTENSIONS if f.endswith(e)]) > 0:
                    t = make_template_info(os.path.join(dirpath, f), dirs)
                    # templates need to be able to search others:
                    t.all_templates = templates
                    templates.add(t)
    return templates

def get_python_code(paths):
    """
    Returns all Python code, as a list of tuples, each one being:
     (filename, list of lines)
    """
    retval = []
    for p in paths:
        for (dirpath, dirnames, filenames) in os.walk(p):
            for f in filenames:
                if len([True for e in PYTHON_SOURCE_EXTENSIONS if f.endswith(e)]) > 0:
                    fn = os.path.join(dirpath, f)
                    fd = open(fn)
                    content = [l.decode(PYTHON_ENCODING) for l in fd.readlines()]
                    fd.close()
                    retval.append((fn, content))
    return retval

def search_python_list(python_code, template_names):
    """
    Searches python code for a list of template names.
    Returns a list of tuples, each one being:
     (filename, line number)
    """
    retval = []
    for tn in template_names:
        retval.extend(search_python(python_code, tn))
    retval = list(set(retval))
    retval.sort()
    return retval

def search_python(python_code, template_name):
    """
    Searches Python code for a template name.
    Returns a list of tuples, each one being:
     (filename, line number)
    """
    retval = []
    for fn, content in python_code:
        for ln, line in enumerate(content):
            if ((u'"%s"' % template_name) in line) or \
               ((u"'%s'" % template_name) in line):
                retval.append((fn, ln + 1))
    return retval

def main(pythonpaths):
    template_dirs = get_template_dirs()
    templates = get_templates(template_dirs)
    python_code = get_python_code(pythonpaths)
    for t in templates:
        # Logic
        form_matches = t.post_form_info()
        num_post_forms = len(form_matches)
        form_lines_without_token = [ln for (ln, has_token) in form_matches if not has_token]
        if num_post_forms == 0:
            continue
        to_search = [rf for rt in t.related_templates() for rf in rt.relative_filenames]
        found = search_python_list(python_code, to_search)

        # Display:
        print t.absolute_filename
        for r in t.relative_filenames:
            print u"  AKA %s" % r
        print u"  POST forms: %s" % num_post_forms
        print u"  With token: %s" % (num_post_forms - len(form_lines_without_token))
        if form_lines_without_token:
            print u"  Without token:"
            for ln in form_lines_without_token:
                print "%s:%d:" % (t.absolute_filename, ln)
        print
        print u"  Searching for:"
        for r in to_search:
            print u"    " + r
        print
        print u"  Found:"
        if len(found) == 0:
            print "    Nothing"
        else:
            for fn, ln in found:
                print "%s:%d:" % (fn, ln)

        print
        print "----"


if __name__ == '__main__':
    # Hacky argument parsing, one day I'll learn OptParse...
    args = list(sys.argv[1:])
    if len(args) > 0:
        if args[0] in ['--help', '-h', '-?', '--usage']:
            print USAGE
            sys.exit(0)
        else:
            if args[0].startswith('--settings='):
                module = args[0][len('--settings='):]
                os.environ["DJANGO_SETTINGS_MODULE"] = module
                args = args[1:]

            if args[0].startswith('-'):
                print "Unknown option: %s" % args[0]
                print USAGE
                sys.exit(1)

            pythonpaths = args

            if os.environ.get("DJANGO_SETTINGS_MODULE", None) is None:
                print "You need to set DJANGO_SETTINGS_MODULE or use the '--settings' parameter"
                sys.exit(1)
            if len(pythonpaths) == 0:
                print "Unrecognised command: %s" % command
                print USAGE
                sys.exit(1)

            main(pythonpaths)

    else:
        # no args
        print USAGE
        sys.exit(0)

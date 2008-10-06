"""
Wrapper for loading templates from the filesystem.
"""

from django.conf import settings
from django.template import TemplateDoesNotExist
from django.utils._os import safe_join

def get_template_sources(template_name, template_dirs=None):
    """
    Returns the absolute paths to "template_name", when appended to each
    directory in "template_dirs". Any paths that don't lie inside one of the
    template dirs are excluded from the result set, for security reasons.
    """
    if not template_dirs:
        template_dirs = settings.TEMPLATE_DIRS
    for template_dir in template_dirs:
        try:
            yield safe_join(template_dir, template_name)
        except UnicodeDecodeError:
            # The template dir name was a bytestring that wasn't valid UTF-8.
            raise
        except ValueError:
            # The joined path was located outside of this particular
            # template_dir (it might be inside another one, so this isn't
            # fatal).
            pass

def load_template_source(template_name, template_dirs=None):
    tried = []
    for filepath in get_template_sources(template_name, template_dirs):
        try:
            return (open(filepath).read().decode(settings.FILE_CHARSET), filepath)
        except IOError:
            tried.append(filepath)
    if tried:
        error_msg = "Tried %s" % tried
    else:
        error_msg = "Your TEMPLATE_DIRS setting is empty. Change it to point to at least one template directory."
    raise TemplateDoesNotExist, error_msg
load_template_source.is_usable = True

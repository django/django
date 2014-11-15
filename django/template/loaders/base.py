from django.template.base import TemplateDoesNotExist
from django.template.loader import get_template_from_string, make_origin


class Loader(object):
    is_usable = False

    def __init__(self, *args, **kwargs):
        # XXX dropping arguments silently may not be the best idea.
        pass

    def __call__(self, template_name, template_dirs=None):
        return self.load_template(template_name, template_dirs)

    def load_template(self, template_name, template_dirs=None):
        source, display_name = self.load_template_source(
            template_name, template_dirs)
        origin = make_origin(
            display_name, self.load_template_source,
            template_name, template_dirs)

        try:
            template = get_template_from_string(source, origin, template_name)
        except TemplateDoesNotExist:
            # If compiling the template we found raises TemplateDoesNotExist,
            # back off to returning the source and display name for the
            # template we were asked to load. This allows for correct
            # identification of the actual template that does not exist.
            return source, display_name
        else:
            return template, None

    def load_template_source(self, template_name, template_dirs=None):
        """
        Returns a tuple containing the source and origin for the given
        template name.
        """
        raise NotImplementedError(
            "subclasses of Loader must provide "
            "a load_template_source() method")

    def reset(self):
        """
        Resets any state maintained by the loader instance (e.g. cached
        templates or cached loader modules).
        """
        pass

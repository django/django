from django.template.base import Template, TemplateDoesNotExist


class Loader(object):
    is_usable = False
    # Only used to raise a deprecation warning. Remove in Django 1.10.
    _accepts_engine_in_init = True

    def __init__(self, engine):
        self.engine = engine

    def __call__(self, template_name, template_dirs=None):
        return self.load_template(template_name, template_dirs)

    def load_template(self, template_name, template_dirs=None):
        source, display_name = self.load_template_source(
            template_name, template_dirs)
        origin = self.engine.make_origin(
            display_name, self.load_template_source,
            template_name, template_dirs)

        try:
            template = Template(source, origin, template_name, self.engine)
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

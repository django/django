from django.template import Template, TemplateDoesNotExist


class Loader:

    def __init__(self, engine):
        self.engine = engine

    def get_template(self, template_name, skip=None):
        """
        Call self.get_template_sources() and return a Template object for
        the first template matching template_name. If skip is provided, ignore
        template origins in skip. This is used to avoid recursion during
        template extending.
        """
        tried = []

        for origin in self.get_template_sources(template_name):
            if skip is not None and origin in skip:
                tried.append((origin, 'Skipped'))
                continue

            try:
                contents = self.get_contents(origin)
            except TemplateDoesNotExist:
                tried.append((origin, 'Source does not exist'))
                continue
            else:
                return Template(
                    contents, origin, origin.template_name, self.engine,
                )

        raise TemplateDoesNotExist(template_name, tried=tried)

    def get_template_sources(self, template_name):
        """
        An iterator that yields possible matching template paths for a
        template name.
        """
        raise NotImplementedError(
            'subclasses of Loader must provide a get_template_sources() method'
        )

    def reset(self):
        """
        Reset any state maintained by the loader instance (e.g. cached
        templates or cached loader modules).
        """
        pass

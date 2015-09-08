import warnings

from django.template import Origin, Template, TemplateDoesNotExist
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.inspect import func_supports_parameter


class Loader(object):
    # Only used to raise a deprecation warning. Remove in Django 1.10.
    _accepts_engine_in_init = True

    def __init__(self, engine):
        self.engine = engine

    def __call__(self, template_name, template_dirs=None):
        # RemovedInDjango20Warning: Allow loaders to be called like functions.
        return self.load_template(template_name, template_dirs)

    def get_template(self, template_name, template_dirs=None, skip=None):
        """
        Calls self.get_template_sources() and returns a Template object for
        the first template matching template_name. If skip is provided,
        template origins in skip are ignored. This is used to avoid recursion
        during template extending.
        """
        tried = []

        args = [template_name]
        # RemovedInDjango20Warning: Add template_dirs for compatibility with
        # old loaders
        if func_supports_parameter(self.get_template_sources, 'template_dirs'):
            args.append(template_dirs)

        for origin in self.get_template_sources(*args):
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

    def load_template(self, template_name, template_dirs=None):
        warnings.warn(
            'The load_template() method is deprecated. Use get_template() '
            'instead.', RemovedInDjango20Warning,
        )
        source, display_name = self.load_template_source(
            template_name, template_dirs,
        )
        origin = Origin(
            name=display_name,
            template_name=template_name,
            loader=self,
        )
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

    def get_template_sources(self, template_name):
        """
        An iterator that yields possible matching template paths for a
        template name.
        """
        raise NotImplementedError(
            'subclasses of Loader must provide a get_template_sources() method'
        )

    def load_template_source(self, template_name, template_dirs=None):
        """
        RemovedInDjango20Warning: Returns a tuple containing the source and
        origin for the given template name.
        """
        raise NotImplementedError(
            'subclasses of Loader must provide a load_template_source() method'
        )

    def reset(self):
        """
        Resets any state maintained by the loader instance (e.g. cached
        templates or cached loader modules).
        """
        pass

    @property
    def supports_recursion(self):
        """
        RemovedInDjango20Warning: This is an internal property used by the
        ExtendsNode during the deprecation of non-recursive loaders.
        """
        return hasattr(self, 'get_contents')

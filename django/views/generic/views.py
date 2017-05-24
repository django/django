# coding: utf-8
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseRedirect
# from django.shortcuts import render
from django.template.response import TemplateResponse
from django.views.generic import View


# Main genericview class
class GenericView(View):
    """
    A generic base class for building template and/or form views.
    """
    form_class = None
    template_name = None

    # Form instantiation

    def get_form_class(self):
        """
        Returns the form class to use in this view.
        """
        if self.form_class is not None:
            return self.form_class

        msg = "'%s' must either define 'form_class' or override 'get_form_class()'"
        raise ImproperlyConfigured(msg % self.__class__.__name__)

    def get_form(self, data=None, files=None, **kwargs):
        """
        Given `data` and `files` QueryDicts, and optionally other named
        arguments, and returns a form.
        """
        cls = self.get_form_class()
        return cls(data=data, files=files, **kwargs)

    # Response rendering

    def get_template_names(self):
        """
        Returns a set of template names that may be used when rendering
        the response.
        """
        if self.template_name is not None:
            return [self.template_name]

        msg = "'%s' must either define 'template_name' or override 'get_template_names()'"
        raise ImproperlyConfigured(msg % self.__class__.__name__)

    def get_context_data(self, **kwargs):
        """
        Takes a set of keyword arguments to use as the base context, and
        returns a context dictionary to use for the view, additionally adding
        in 'view'.
        """
        kwargs['view'] = self
        return kwargs

    def render(self, context):
        """
        Given a context dictionary, returns an HTTP response.
        """
        return TemplateResponse(
            request=self.request,
            template=self.get_template_names(),
            context=context
        )


# templateview class
class TemplateView(GenericView):
    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return self.render(context)


# FormView class
class FormView(GenericView):
    success_url = None

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        context = self.get_context_data(form=form)
        return self.render(context)

    def post(self, request, *args, **kwargs):
        form = self.get_form(data=request.POST, files=request.FILES)
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        return self.render(context)

    def get_success_url(self):
        if self.success_url is None:
            msg = "'%s' must define 'success_url' or override 'get_success_url()'"
            raise ImproperlyConfigured(msg % self.__class__.__name__)
        return self.success_url

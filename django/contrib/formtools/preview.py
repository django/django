"""
Formtools Preview application.
"""

import cPickle as pickle

from django.conf import settings
from django.http import Http404
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.hashcompat import md5_constructor
from django.contrib.formtools.utils import security_hash

AUTO_ID = 'formtools_%s' # Each form here uses this as its auto_id parameter.

class FormPreview(object):
    preview_template = 'formtools/preview.html'
    form_template = 'formtools/form.html'

    # METHODS SUBCLASSES SHOULDN'T OVERRIDE ###################################

    def __init__(self, form):
        # form should be a Form class, not an instance.
        self.form, self.state = form, {}

    def __call__(self, request, *args, **kwargs):
        stage = {'1': 'preview', '2': 'post'}.get(request.POST.get(self.unused_name('stage')), 'preview')
        self.parse_params(*args, **kwargs)
        try:
            method = getattr(self, stage + '_' + request.method.lower())
        except AttributeError:
            raise Http404
        return method(request)

    def unused_name(self, name):
        """
        Given a first-choice name, adds an underscore to the name until it
        reaches a name that isn't claimed by any field in the form.

        This is calculated rather than being hard-coded so that no field names
        are off-limits for use in the form.
        """
        while 1:
            try:
                f = self.form.base_fields[name]
            except KeyError:
                break # This field name isn't being used by the form.
            name += '_'
        return name

    def preview_get(self, request):
        "Displays the form"
        f = self.form(auto_id=AUTO_ID)
        return render_to_response(self.form_template,
            {'form': f, 'stage_field': self.unused_name('stage'), 'state': self.state},
            context_instance=RequestContext(request))

    def preview_post(self, request):
        "Validates the POST data. If valid, displays the preview page. Else, redisplays form."
        f = self.form(request.POST, auto_id=AUTO_ID)
        context = {'form': f, 'stage_field': self.unused_name('stage'), 'state': self.state}
        if f.is_valid():
            context['hash_field'] = self.unused_name('hash')
            context['hash_value'] = self.security_hash(request, f)
            return render_to_response(self.preview_template, context, context_instance=RequestContext(request))
        else:
            return render_to_response(self.form_template, context, context_instance=RequestContext(request))

    def post_post(self, request):
        "Validates the POST data. If valid, calls done(). Else, redisplays form."
        f = self.form(request.POST, auto_id=AUTO_ID)
        if f.is_valid():
            if self.security_hash(request, f) != request.POST.get(self.unused_name('hash')):
                return self.failed_hash(request) # Security hash failed.
            return self.done(request, f.cleaned_data)
        else:
            return render_to_response(self.form_template,
                {'form': f, 'stage_field': self.unused_name('stage'), 'state': self.state},
                context_instance=RequestContext(request))

    # METHODS SUBCLASSES MIGHT OVERRIDE IF APPROPRIATE ########################

    def parse_params(self, *args, **kwargs):
        """
        Given captured args and kwargs from the URLconf, saves something in
        self.state and/or raises Http404 if necessary.

        For example, this URLconf captures a user_id variable:

            (r'^contact/(?P<user_id>\d{1,6})/$', MyFormPreview(MyForm)),

        In this case, the kwargs variable in parse_params would be
        {'user_id': 32} for a request to '/contact/32/'. You can use that
        user_id to make sure it's a valid user and/or save it for later, for
        use in done().
        """
        pass

    def security_hash(self, request, form):
        """
        Calculates the security hash for the given HttpRequest and Form instances.

        Subclasses may want to take into account request-specific information,
        such as the IP address.
        """
        return security_hash(request, form)

    def failed_hash(self, request):
        "Returns an HttpResponse in the case of an invalid security hash."
        return self.preview_post(request)

    # METHODS SUBCLASSES MUST OVERRIDE ########################################

    def done(self, request, cleaned_data):
        """
        Does something with the cleaned_data and returns an
        HttpResponseRedirect.
        """
        raise NotImplementedError('You must define a done() method on your %s subclass.' % self.__class__.__name__)

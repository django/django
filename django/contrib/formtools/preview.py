"""
Formtools Preview application.

This is an abstraction of the following workflow:

    "Display an HTML form, force a preview, then do something with the submission."

Given a django.newforms.Form object that you define, this takes care of the
following:

    * Displays the form as HTML on a Web page.
    * Validates the form data once it's submitted via POST.
        * If it's valid, displays a preview page.
        * If it's not valid, redisplays the form with error messages.
    * At the preview page, if the preview confirmation button is pressed, calls
      a hook that you define -- a done() method.

The framework enforces the required preview by passing a shared-secret hash to
the preview page. If somebody tweaks the form parameters on the preview page,
the form submission will fail the hash comparison test.

Usage
=====

Subclass FormPreview and define a done() method:

    def done(self, request, clean_data):
        # ...

This method takes an HttpRequest object and a dictionary of the form data after
it has been validated and cleaned. It should return an HttpResponseRedirect.

Then, just instantiate your FormPreview subclass by passing it a Form class,
and pass that to your URLconf, like so:

    (r'^post/$', MyFormPreview(MyForm)),

The FormPreview class has a few other hooks. See the docstrings in the source
code below.

The framework also uses two templates: 'formtools/preview.html' and
'formtools/form.html'. You can override these by setting 'preview_template' and
'form_template' attributes on your FormPreview subclass. See
django/contrib/formtools/templates for the default templates.
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.shortcuts import render_to_response
import cPickle as pickle
import md5

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
                f = self.form.fields[name]
            except KeyError:
                break # This field name isn't being used by the form.
            name += '_'
        return name

    def preview_get(self, request):
        "Displays the form"
        f = self.form(auto_id=AUTO_ID)
        return render_to_response(self.form_template, {'form': f, 'stage_field': self.unused_name('stage'), 'state': self.state})

    def preview_post(self, request):
        "Validates the POST data. If valid, displays the preview page. Else, redisplays form."
        f = self.form(request.POST, auto_id=AUTO_ID)
        context = {'form': f, 'stage_field': self.unused_name('stage'), 'state': self.state}
        if f.is_valid():
            context['hash_field'] = self.unused_name('hash')
            context['hash_value'] = self.security_hash(request, f)
            return render_to_response(self.preview_template, context)
        else:
            return render_to_response(self.form_template, context)

    def post_post(self, request):
        "Validates the POST data. If valid, calls done(). Else, redisplays form."
        f = self.form(request.POST, auto_id=AUTO_ID)
        if f.is_valid():
            if self.security_hash(request, f) != request.POST.get(self.unused_name('hash')):
                return self.failed_hash(request) # Security hash failed.
            return self.done(request, f.clean_data)
        else:
            return render_to_response(self.form_template, {'form': f, 'stage_field': self.unused_name('stage'), 'state': self.state})

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
        Calculates the security hash for the given Form instance.

        This creates a list of the form field names/values in a deterministic
        order, pickles the result with the SECRET_KEY setting and takes an md5
        hash of that.

        Subclasses may want to take into account request-specific information
        such as the IP address.
        """
        data = [(bf.name, bf.data) for bf in form] + [settings.SECRET_KEY]
        # Use HIGHEST_PROTOCOL because it's the most efficient. It requires
        # Python 2.3, but Django requires 2.3 anyway, so that's OK.
        pickled = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        return md5.new(pickled).hexdigest()

    def failed_hash(self, request):
        "Returns an HttpResponse in the case of an invalid security hash."
        return self.preview_post(request)

    # METHODS SUBCLASSES MUST OVERRIDE ########################################

    def done(self, request, clean_data):
        "Does something with the clean_data and returns an HttpResponseRedirect."
        raise NotImplementedError('You must define a done() method on your %s subclass.' % self.__class__.__name__)

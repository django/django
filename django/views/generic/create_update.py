from django.forms.models import ModelFormMetaclass, ModelForm
from django.template import RequestContext, loader
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.core.xheaders import populate_xheaders
from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured
from django.utils.translation import ugettext
from django.contrib.auth.views import redirect_to_login
from django.views.generic import GenericViewError


def apply_extra_context(extra_context, context):
    """
    Adds items from extra_context dict to context.  If a value in extra_context
    is callable, then it is called and the result is added to context.
    """
    for key, value in extra_context.iteritems():
        if callable(value):
            context[key] = value()
        else:
            context[key] = value

def get_model_and_form_class(model, form_class):
    """
    Returns a model and form class based on the model and form_class
    parameters that were passed to the generic view.

    If ``form_class`` is given then its associated model will be returned along
    with ``form_class`` itself.  Otherwise, if ``model`` is given, ``model``
    itself will be returned along with a ``ModelForm`` class created from
    ``model``.
    """
    if form_class:
        return form_class._meta.model, form_class
    if model:
        # The inner Meta class fails if model = model is used for some reason.
        tmp_model = model
        # TODO: we should be able to construct a ModelForm without creating
        # and passing in a temporary inner class.
        class Meta:
            model = tmp_model
        class_name = model.__name__ + 'Form'
        form_class = ModelFormMetaclass(class_name, (ModelForm,), {'Meta': Meta})
        return model, form_class
    raise GenericViewError("Generic view must be called with either a model or"
                           " form_class argument.")

def redirect(post_save_redirect, obj):
    """
    Returns a HttpResponseRedirect to ``post_save_redirect``.

    ``post_save_redirect`` should be a string, and can contain named string-
    substitution place holders of ``obj`` field names.

    If ``post_save_redirect`` is None, then redirect to ``obj``'s URL returned
    by ``get_absolute_url()``.  If ``obj`` has no ``get_absolute_url`` method,
    then raise ImproperlyConfigured.

    This function is meant to handle the post_save_redirect parameter to the
    ``create_object`` and ``update_object`` views.
    """
    if post_save_redirect:
        return HttpResponseRedirect(post_save_redirect % obj.__dict__)
    elif hasattr(obj, 'get_absolute_url'):
        return HttpResponseRedirect(obj.get_absolute_url())
    else:
        raise ImproperlyConfigured(
            "No URL to redirect to.  Either pass a post_save_redirect"
            " parameter to the generic view or define a get_absolute_url"
            " method on the Model.")

def lookup_object(model, object_id, slug, slug_field):
    """
    Return the ``model`` object with the passed ``object_id``.  If
    ``object_id`` is None, then return the object whose ``slug_field``
    equals the passed ``slug``.  If ``slug`` and ``slug_field`` are not passed,
    then raise Http404 exception.
    """
    lookup_kwargs = {}
    if object_id:
        lookup_kwargs['%s__exact' % model._meta.pk.name] = object_id
    elif slug and slug_field:
        lookup_kwargs['%s__exact' % slug_field] = slug
    else:
        raise GenericViewError(
            "Generic view must be called with either an object_id or a"
            " slug/slug_field.")
    try:
        return model.objects.get(**lookup_kwargs)
    except ObjectDoesNotExist:
        raise Http404("No %s found for %s"
                      % (model._meta.verbose_name, lookup_kwargs))

def create_object(request, model=None, template_name=None,
        template_loader=loader, extra_context=None, post_save_redirect=None,
        login_required=False, context_processors=None, form_class=None):
    """
    Generic object-creation function.

    Templates: ``<app_label>/<model_name>_form.html``
    Context:
        form
            the form for the object
    """
    if extra_context is None: extra_context = {}
    if login_required and not request.user.is_authenticated():
        return redirect_to_login(request.path)

    model, form_class = get_model_and_form_class(model, form_class)
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            new_object = form.save()
            if request.user.is_authenticated():
                request.user.message_set.create(message=ugettext("The %(verbose_name)s was created successfully.") % {"verbose_name": model._meta.verbose_name})
            return redirect(post_save_redirect, new_object)
    else:
        form = form_class()

    # Create the template, context, response
    if not template_name:
        template_name = "%s/%s_form.html" % (model._meta.app_label, model._meta.object_name.lower())
    t = template_loader.get_template(template_name)
    c = RequestContext(request, {
        'form': form,
    }, context_processors)
    apply_extra_context(extra_context, c)
    return HttpResponse(t.render(c))

def update_object(request, model=None, object_id=None, slug=None,
        slug_field='slug', template_name=None, template_loader=loader,
        extra_context=None, post_save_redirect=None, login_required=False,
        context_processors=None, template_object_name='object',
        form_class=None):
    """
    Generic object-update function.

    Templates: ``<app_label>/<model_name>_form.html``
    Context:
        form
            the form for the object
        object
            the original object being edited
    """
    if extra_context is None: extra_context = {}
    if login_required and not request.user.is_authenticated():
        return redirect_to_login(request.path)

    model, form_class = get_model_and_form_class(model, form_class)
    obj = lookup_object(model, object_id, slug, slug_field)

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            obj = form.save()
            if request.user.is_authenticated():
                request.user.message_set.create(message=ugettext("The %(verbose_name)s was updated successfully.") % {"verbose_name": model._meta.verbose_name})
            return redirect(post_save_redirect, obj)
    else:
        form = form_class(instance=obj)

    if not template_name:
        template_name = "%s/%s_form.html" % (model._meta.app_label, model._meta.object_name.lower())
    t = template_loader.get_template(template_name)
    c = RequestContext(request, {
        'form': form,
        template_object_name: obj,
    }, context_processors)
    apply_extra_context(extra_context, c)
    response = HttpResponse(t.render(c))
    populate_xheaders(request, response, model, getattr(obj, obj._meta.pk.attname))
    return response

def delete_object(request, model, post_delete_redirect, object_id=None,
        slug=None, slug_field='slug', template_name=None,
        template_loader=loader, extra_context=None, login_required=False,
        context_processors=None, template_object_name='object'):
    """
    Generic object-delete function.

    The given template will be used to confirm deletetion if this view is
    fetched using GET; for safty, deletion will only be performed if this
    view is POSTed.

    Templates: ``<app_label>/<model_name>_confirm_delete.html``
    Context:
        object
            the original object being deleted
    """
    if extra_context is None: extra_context = {}
    if login_required and not request.user.is_authenticated():
        return redirect_to_login(request.path)

    obj = lookup_object(model, object_id, slug, slug_field)

    if request.method == 'POST':
        obj.delete()
        if request.user.is_authenticated():
            request.user.message_set.create(message=ugettext("The %(verbose_name)s was deleted.") % {"verbose_name": model._meta.verbose_name})
        return HttpResponseRedirect(post_delete_redirect)
    else:
        if not template_name:
            template_name = "%s/%s_confirm_delete.html" % (model._meta.app_label, model._meta.object_name.lower())
        t = template_loader.get_template(template_name)
        c = RequestContext(request, {
            template_object_name: obj,
        }, context_processors)
        apply_extra_context(extra_context, c)
        response = HttpResponse(t.render(c))
        populate_xheaders(request, response, model, getattr(obj, obj._meta.pk.attname))
        return response

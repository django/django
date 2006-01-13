from django.core.xheaders import populate_xheaders
from django.template import loader
from django.core import formfields, meta
from django.views.auth.login import redirect_to_login
from django.template import RequestContext
from django.core.paginator import ObjectPaginator, InvalidPage
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured

def create_object(request, model, template_name=None,
        template_loader=loader, extra_context={}, post_save_redirect=None,
        login_required=False, follow=None, context_processors=None):
    """
    Generic object-creation function.

    Templates: ``<app_label>/<model_name>_form``
    Context:
        form
            the form wrapper for the object
    """
    if login_required and request.user.is_anonymous():
        return redirect_to_login(request.path)

    manipulator = model.AddManipulator(follow=follow)
    if request.POST:
        # If data was POSTed, we're trying to create a new object
        new_data = request.POST.copy()

        if model._meta.has_field_type(meta.FileField):
            new_data.update(request.FILES)

        # Check for errors
        errors = manipulator.get_validation_errors(new_data)
        manipulator.do_html2python(new_data)

        if not errors:
            # No errors -- this means we can save the data!
            new_object = manipulator.save(new_data)

            if not request.user.is_anonymous():
                request.user.add_message("The %s was created sucessfully." % model._meta.verbose_name)

            # Redirect to the new object: first by trying post_save_redirect,
            # then by obj.get_absolute_url; fail if neither works.
            if post_save_redirect:
                return HttpResponseRedirect(post_save_redirect % new_object.__dict__)
            elif hasattr(new_object, 'get_absolute_url'):
                return HttpResponseRedirect(new_object.get_absolute_url())
            else:
                raise ImproperlyConfigured("No URL to redirect to from generic create view.")
    else:
        # No POST, so we want a brand new form without any data or errors
        errors = {}
        new_data = manipulator.flatten_data()

    # Create the FormWrapper, template, context, response
    form = formfields.FormWrapper(manipulator, new_data, errors)
    if not template_name:
        template_name = "%s/%s_form" % (model._meta.app_label, model._meta.object_name.lower())
    t = template_loader.get_template(template_name)
    c = RequestContext(request, {
        'form': form,
    }, context_processors)
    for key, value in extra_context.items():
        if callable(value):
            c[key] = value()
        else:
            c[key] = value
    return HttpResponse(t.render(c))

def update_object(request, model, object_id=None, slug=None,
        slug_field=None, template_name=None, template_loader=loader,
        extra_lookup_kwargs={}, extra_context={}, post_save_redirect=None,
        login_required=False, follow=None, context_processors=None):
    """
    Generic object-update function.

    Templates: ``<app_label>/<model_name>_form``
    Context:
        form
            the form wrapper for the object
        object
            the original object being edited
    """
    if login_required and request.user.is_anonymous():
        return redirect_to_login(request.path)

    # Look up the object to be edited
    lookup_kwargs = {}
    if object_id:
        lookup_kwargs['%s__exact' % model._meta.pk.name] = object_id
    elif slug and slug_field:
        lookup_kwargs['%s__exact' % slug_field] = slug
    else:
        raise AttributeError("Generic edit view must be called with either an object_id or a slug/slug_field")
    lookup_kwargs.update(extra_lookup_kwargs)
    try:
        object = model._default_manager.get_object(**lookup_kwargs)
    except ObjectDoesNotExist:
        raise Http404, "No %s found for %s" % (model._meta.verbose_name, lookup_kwargs)

    manipulator = model.ChangeManipulator(object.id, follow=follow)

    if request.POST:
        new_data = request.POST.copy()
        errors = manipulator.get_validation_errors(new_data)
        manipulator.do_html2python(new_data)
        if not errors:
            manipulator.save(new_data)

            if not request.user.is_anonymous():
                request.user.add_message("The %s was updated sucessfully." % model._meta.verbose_name)

            # Do a post-after-redirect so that reload works, etc.
            if post_save_redirect:
                return HttpResponseRedirect(post_save_redirect % object.__dict__)
            elif hasattr(object, 'get_absolute_url'):
                return HttpResponseRedirect(object.get_absolute_url())
            else:
                raise ImproperlyConfigured("No URL to redirect to from generic create view.")
    else:
        errors = {}
        # This makes sure the form acurate represents the fields of the place.
        new_data = manipulator.flatten_data()

    form = formfields.FormWrapper(manipulator, new_data, errors)
    if not template_name:
        template_name = "%s/%s_form" % (model._meta.app_label, model._meta.object_name.lower())
    t = template_loader.get_template(template_name)
    c = RequestContext(request, {
        'form': form,
        'object': object,
    }, context_processors)
    for key, value in extra_context.items():
        if callable(value):
            c[key] = value()
        else:
            c[key] = value
    response = HttpResponse(t.render(c))
    populate_xheaders(request, response, model, getattr(object, object._meta.pk.name))
    return response

def delete_object(request, model, post_delete_redirect,
        object_id=None, slug=None, slug_field=None, template_name=None,
        template_loader=loader, extra_lookup_kwargs={}, extra_context={},
        login_required=False, context_processors=None):
    """
    Generic object-delete function.

    The given template will be used to confirm deletetion if this view is
    fetched using GET; for safty, deletion will only be performed if this
    view is POSTed.

    Templates: ``<app_label>/<model_name>_confirm_delete``
    Context:
        object
            the original object being deleted
    """
    if login_required and request.user.is_anonymous():
        return redirect_to_login(request.path)

    # Look up the object to be edited
    lookup_kwargs = {}
    if object_id:
        lookup_kwargs['%s__exact' % model._meta.pk.name] = object_id
    elif slug and slug_field:
        lookup_kwargs['%s__exact' % slug_field] = slug
    else:
        raise AttributeError("Generic delete view must be called with either an object_id or a slug/slug_field")
    lookup_kwargs.update(extra_lookup_kwargs)
    try:
        object = model._default_manager.get_object(**lookup_kwargs)
    except ObjectDoesNotExist:
        raise Http404, "No %s found for %s" % (model._meta.app_label, lookup_kwargs)

    if request.META['REQUEST_METHOD'] == 'POST':
        object.delete()
        if not request.user.is_anonymous():
            request.user.add_message("The %s was deleted." % model._meta.verbose_name)
        return HttpResponseRedirect(post_delete_redirect)
    else:
        if not template_name:
            template_name = "%s/%s_confirm_delete" % (model._meta.app_label, model._meta.object_name.lower())
        t = template_loader.get_template(template_name)
        c = RequestContext(request, {
            'object': object,
        }, context_processors)
        for key, value in extra_context.items():
            if callable(value):
                c[key] = value()
            else:
                c[key] = value
        response = HttpResponse(t.render(c))
        populate_xheaders(request, response, model, getattr(object, object._meta.pk.name))
        return response

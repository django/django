"""
Built-in, globally-available admin actions.
"""

from django.contrib import messages
from django.contrib.admin import helpers
from django.contrib.admin.decorators import action
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _, gettext_lazy, ngettext


@action(
    permissions=['delete'],
    description=gettext_lazy('Delete selected %(verbose_name_plural)s'),
)
def delete_selected(modeladmin, request, queryset):
    """
    Default action which deletes the selected objects.

    This action first displays a confirmation page which shows all the
    deletable objects, or, if the user has no permission one of the related
    childs (foreignkeys), a "permission denied" message.

    Next, it deletes all selected objects and redirects back to the change list.
    """
    opts = modeladmin.model._meta
    app_label = opts.app_label

    # Populate deletable_objects, a data structure of all related objects that
    # will also be deleted.
    deletable_objects, model_count, perms_needed, protected = modeladmin.get_deleted_objects(queryset, request)

    # The user has already confirmed the deletion.
    # Do the deletion and return None to display the change list view again.
    if request.POST.get('post') and not protected:
        if perms_needed:
            raise PermissionDenied
        n = queryset.count()
        if n:
            for obj in queryset:
                obj_display = str(obj)
                modeladmin.log_deletion(request, obj, obj_display)
            modeladmin.delete_queryset(request, queryset)
            modeladmin.message_user(
                request,
                ngettext(
                    "Successfully deleted %(count)d %(item)s.",
                    "Successfully deleted %(count)d %(items)s.",
                    n,
                )
                % {
                    "count": n,
                    "item": modeladmin.opts.verbose_name,
                    "items": modeladmin.opts.verbose_name_plural,
                },
                messages.SUCCESS,
            )
        # Return None to display the change list page again.
        return None

    object_name = queryset.model._meta.verbose_name
    objects_name = queryset.model._meta.verbose_name_plural

    if perms_needed or protected:
        title = ngettext(
            "Cannot delete %(item)s", "Cannot delete %(items)s", queryset.count()
        ) % {"item": object_name, "items": objects_name}
    else:
        title = _("Are you sure?")

    context = {
        **modeladmin.admin_site.each_context(request),
        'title': title,
        'subtitle': None,
        'object_name': str(object_name),
        'objects_name': str(objects_name),
        'deletable_objects': [deletable_objects],
        'model_count': dict(model_count).items(),
        'queryset': queryset,
        'perms_lacking': perms_needed,
        'protected': protected,
        'opts': opts,
        'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        'media': modeladmin.media,
    }

    request.current_app = modeladmin.admin_site.name

    # Display the confirmation page
    return TemplateResponse(request, modeladmin.delete_selected_confirmation_template or [
        "admin/%s/%s/delete_selected_confirmation.html" % (app_label, opts.model_name),
        "admin/%s/delete_selected_confirmation.html" % app_label,
        "admin/delete_selected_confirmation.html"
    ], context)

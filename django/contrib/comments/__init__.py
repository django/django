from django.conf import settings
from django.core import urlresolvers
from django.core.exceptions import ImproperlyConfigured

# Attributes required in the top-level app for COMMENTS_APP
REQUIRED_COMMENTS_APP_ATTRIBUTES = ["get_model", "get_form", "get_form_target"]

def get_comment_app():
    """
    Get the comment app (i.e. "django.contrib.comments") as defined in the settings
    """
    # Make sure the app's in INSTALLED_APPS
    comments_app = getattr(settings, 'COMMENTS_APP', 'django.contrib.comments')
    if comments_app not in settings.INSTALLED_APPS:
        raise ImproperlyConfigured("The COMMENTS_APP (%r) "\
                                   "must be in INSTALLED_APPS" % settings.COMMENTS_APP)

    # Try to import the package
    try:
        package = __import__(settings.COMMENTS_APP, '', '', [''])
    except ImportError:
        raise ImproperlyConfigured("The COMMENTS_APP setting refers to "\
                                   "a non-existing package.")

    # Make sure some specific attributes exist inside that package.
    for attribute in REQUIRED_COMMENTS_APP_ATTRIBUTES:
        if not hasattr(package, attribute):
            raise ImproperlyConfigured("The COMMENTS_APP package %r does not "\
                                       "define the (required) %r function" % \
                                            (package, attribute))

    return package

def get_model():
    from django.contrib.comments.models import Comment
    return Comment

def get_form():
    from django.contrib.comments.forms import CommentForm
    return CommentForm

def get_form_target():
    return urlresolvers.reverse("django.contrib.comments.views.comments.post_comment")

def get_flag_url(comment):
    """
    Get the URL for the "flag this comment" view.
    """
    if settings.COMMENTS_APP != __name__ and hasattr(get_comment_app(), "get_flag_url"):
        return get_comment_app().get_flag_url(comment)
    else:
        return urlresolvers.reverse("django.contrib.comments.views.moderation.flag", args=(comment.id,))

def get_delete_url(comment):
    """
    Get the URL for the "delete this comment" view.
    """
    if settings.COMMENTS_APP != __name__ and hasattr(get_comment_app(), "get_delete_url"):
        return get_comment_app().get_flag_url(get_delete_url)
    else:
        return urlresolvers.reverse("django.contrib.comments.views.moderation.delete", args=(comment.id,))

def get_approve_url(comment):
    """
    Get the URL for the "approve this comment from moderation" view.
    """
    if settings.COMMENTS_APP != __name__ and hasattr(get_comment_app(), "get_approve_url"):
        return get_comment_app().get_approve_url(comment)
    else:
        return urlresolvers.reverse("django.contrib.comments.views.moderation.approve", args=(comment.id,))

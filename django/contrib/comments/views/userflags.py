from django.core import template_loader
from django.core.extensions import DjangoContext as Context
from django.core.exceptions import Http404
from django.models.comments import comments, moderatordeletions, userflags
from django.views.decorators.auth import login_required
from django.utils.httpwrappers import HttpResponse, HttpResponseRedirect
from django.conf.settings import SITE_ID

def flag(request, comment_id):
    """
    Flags a comment. Confirmation on GET, action on POST.

    Templates: `comments/flag_verify`, `comments/flag_done`
    Context:
        comment
            the flagged `comments.comments` object
    """
    try:
        comment = comments.get_object(pk=comment_id, site__id__exact=SITE_ID)
    except comments.CommentDoesNotExist:
        raise Http404
    if request.POST:
        userflags.flag(comment, request.user)
        return HttpResponseRedirect('%sdone/' % request.path)
    t = template_loader.get_template('comments/flag_verify')
    c = Context(request, {
        'comment': comment,
    })
    return HttpResponse(t.render(c))
flag = login_required(flag)

def flag_done(request, comment_id):
    try:
        comment = comments.get_object(pk=comment_id, site__id__exact=SITE_ID)
    except comments.CommentDoesNotExist:
        raise Http404
    t = template_loader.get_template('comments/flag_done')
    c = Context(request, {
        'comment': comment,
    })
    return HttpResponse(t.render(c))

def delete(request, comment_id):
    """
    Deletes a comment. Confirmation on GET, action on POST.

    Templates: `comments/delete_verify`, `comments/delete_done`
    Context:
        comment
            the flagged `comments.comments` object
    """
    try:
        comment = comments.get_object(pk=comment_id, site__id__exact=SITE_ID)
    except comments.CommentDoesNotExist:
        raise Http404
    if not comments.user_is_moderator(request.user):
        raise Http404
    if request.POST:
        # If the comment has already been removed, silently fail.
        if not comment.is_removed:
            comment.is_removed = True
            comment.save()
            m = moderatordeletions.ModeratorDeletion(None, request.user.id, comment.id, None)
            m.save()
        return HttpResponseRedirect('%sdone/' % request.path)
    t = template_loader.get_template('comments/delete_verify')
    c = Context(request, {
        'comment': comment,
    })
    return HttpResponse(t.render(c))
delete = login_required(delete)

def delete_done(request, comment_id):
    try:
        comment = comments.get_object(pk=comment_id, site__id__exact=SITE_ID)
    except comments.CommentDoesNotExist:
        raise Http404
    t = template_loader.get_template('comments/delete_done')
    c = Context(request, {
        'comment': comment,
    })
    return HttpResponse(t.render(c))

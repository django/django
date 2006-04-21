from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import Http404
from django.contrib.comments.models import Comment, ModeratorDeletion, UserFlag
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.conf import settings

def flag(request, comment_id):
    """
    Flags a comment. Confirmation on GET, action on POST.

    Templates: `comments/flag_verify`, `comments/flag_done`
    Context:
        comment
            the flagged `comments.comments` object
    """
    comment = get_object_or_404(Comment,pk=comment_id, site__id__exact=settings.SITE_ID)
    if request.POST:
        UserFlag.objects.flag(comment, request.user)
        return HttpResponseRedirect('%sdone/' % request.path)
    return render_to_response('comments/flag_verify.html', {'comment': comment}, context_instance=RequestContext(request))
flag = login_required(flag)

def flag_done(request, comment_id):
    comment = get_object_or_404(Comment,pk=comment_id, site__id__exact=settings.SITE_ID)
    return render_to_response('comments/flag_done.html', {'comment': comment}, context_instance=RequestContext(request))

def delete(request, comment_id):
    """
    Deletes a comment. Confirmation on GET, action on POST.

    Templates: `comments/delete_verify`, `comments/delete_done`
    Context:
        comment
            the flagged `comments.comments` object
    """
    comment = get_object_or_404(Comment,pk=comment_id, site__id__exact=settings.SITE_ID)
    if not Comment.objects.user_is_moderator(request.user):
        raise Http404
    if request.POST:
        # If the comment has already been removed, silently fail.
        if not comment.is_removed:
            comment.is_removed = True
            comment.save()
            m = ModeratorDeletion(None, request.user.id, comment.id, None)
            m.save()
        return HttpResponseRedirect('%sdone/' % request.path)
    return render_to_response('comments/delete_verify.html', {'comment': comment}, context_instance=RequestContext(request))
delete = login_required(delete)

def delete_done(request, comment_id):
    comment = get_object_or_404(Comment,pk=comment_id, site__id__exact=settings.SITE_ID)
    return render_to_response('comments/delete_done.html', {'comment': comment}, context_instance=RequestContext(request))

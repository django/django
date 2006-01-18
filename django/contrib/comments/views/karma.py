from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.models.comments import comments, karma

def vote(request, comment_id, vote):
    """
    Rate a comment (+1 or -1)

    Templates: `karma_vote_accepted`
    Context:
        comment
            `comments.comments` object being rated
    """
    rating = {'up': 1, 'down': -1}.get(vote, False)
    if not rating:
        raise Http404, "Invalid vote"
    if request.user.is_anonymous():
        raise Http404, _("Anonymous users cannot vote")
    try:
        comment = comments.get_object(pk=comment_id)
    except comments.CommentDoesNotExist:
        raise Http404, _("Invalid comment ID")
    if comment.user_id == request.user.id:
        raise Http404, _("No voting for yourself")
    karma.vote(request.user.id, comment_id, rating)
    # Reload comment to ensure we have up to date karma count
    comment = comments.get_object(pk=comment_id)
    return render_to_response('comments/karma_vote_accepted', {'comment': comment}, context_instance=RequestContext(request))

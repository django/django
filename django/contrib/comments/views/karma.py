from django.core.exceptions import Http404
from django.core.extensions import DjangoContext, render_to_response
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
        raise Http404, "Anonymous users cannot vote"
    try:
        comment = comments.get_object(pk=comment_id)
    except comments.CommentDoesNotExist:
        raise Http404, "Invalid comment ID"
    if comment.user_id == request.user.id:
        raise Http404, "No voting for yourself"
    karma.vote(request.user.id, comment_id, rating)
    # Reload comment to ensure we have up to date karma count
    comment = comments.get_object(pk=comment_id)
    return render_to_response('comments/karma_vote_accepted', {'comment': comment}, context_instance=DjangoContext(request))

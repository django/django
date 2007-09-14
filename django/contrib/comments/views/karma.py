from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.comments.models import Comment, KarmaScore
from django.utils.translation import ugettext as _

def vote(request, comment_id, vote, extra_context=None, context_processors=None):
    """
    Rate a comment (+1 or -1)

    Templates: `karma_vote_accepted`
    Context:
        comment
            `comments.comments` object being rated
    """
    if extra_context is None: extra_context = {}
    rating = {'up': 1, 'down': -1}.get(vote, False)
    if not rating:
        raise Http404, "Invalid vote"
    if not request.user.is_authenticated():
        raise Http404, _("Anonymous users cannot vote")
    try:
        comment = Comment.objects.get(pk=comment_id)
    except Comment.DoesNotExist:
        raise Http404, _("Invalid comment ID")
    if comment.user.id == request.user.id:
        raise Http404, _("No voting for yourself")
    KarmaScore.objects.vote(request.user.id, comment_id, rating)
    # Reload comment to ensure we have up to date karma count
    comment = Comment.objects.get(pk=comment_id)
    return render_to_response('comments/karma_vote_accepted.html', {'comment': comment},
        context_instance=RequestContext(request, extra_context, context_processors))

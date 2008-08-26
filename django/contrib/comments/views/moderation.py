from django import template
from django.conf import settings
from django.shortcuts import get_object_or_404, render_to_response
from django.contrib.auth.decorators import login_required, permission_required
from utils import next_redirect, confirmation_view
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from django.contrib import comments
from django.contrib.comments import signals

#@login_required
def flag(request, comment_id, next=None):
    """
    Flags a comment. Confirmation on GET, action on POST.

    Templates: `comments/flag.html`,
    Context:
        comment
            the flagged `comments.comment` object
    """
    comment = get_object_or_404(comments.get_model(), pk=comment_id, site__pk=settings.SITE_ID)

    # Flag on POST
    if request.method == 'POST':
        flag, created = comments.models.CommentFlag.objects.get_or_create(
            comment = comment,
            user    = request.user,
            flag    = comments.models.CommentFlag.SUGGEST_REMOVAL
        )
        signals.comment_was_flagged.send(
            sender  = comment.__class__,
            comment = comment,
            flag    = flag,
            created = created,
            request = request,
        )
        return next_redirect(request.POST.copy(), next, flag_done, c=comment.pk)

    # Render a form on GET
    else:
        return render_to_response('comments/flag.html',
            {'comment': comment, "next": next},
            template.RequestContext(request)
        )
flag = login_required(flag)

#@permission_required("comments.delete_comment")
def delete(request, comment_id, next=None):
    """
    Deletes a comment. Confirmation on GET, action on POST. Requires the "can
    moderate comments" permission.

    Templates: `comments/delete.html`,
    Context:
        comment
            the flagged `comments.comment` object
    """
    comment = get_object_or_404(comments.get_model(), pk=comment_id, site__pk=settings.SITE_ID)

    # Delete on POST
    if request.method == 'POST':
        # Flag the comment as deleted instead of actually deleting it.
        flag, created = comments.models.CommentFlag.objects.get_or_create(
            comment = comment,
            user    = request.user,
            flag    = comments.models.CommentFlag.MODERATOR_DELETION
        )
        comment.is_removed = True
        comment.save()
        signals.comment_was_flagged.send(
            sender  = comment.__class__,
            comment = comment,
            flag    = flag,
            created = created,
            request = request,
        )
        return next_redirect(request.POST.copy(), next, delete_done, c=comment.pk)

    # Render a form on GET
    else:
        return render_to_response('comments/delete.html',
            {'comment': comment, "next": next},
            template.RequestContext(request)
        )
delete = permission_required("comments.can_moderate")(delete)

#@permission_required("comments.can_moderate")
def approve(request, comment_id, next=None):
    """
    Approve a comment (that is, mark it as public and non-removed). Confirmation
    on GET, action on POST. Requires the "can moderate comments" permission.

    Templates: `comments/approve.html`,
    Context:
        comment
            the `comments.comment` object for approval
    """
    comment = get_object_or_404(comments.get_model(), pk=comment_id, site__pk=settings.SITE_ID)

    # Delete on POST
    if request.method == 'POST':
        # Flag the comment as approved.
        flag, created = comments.models.CommentFlag.objects.get_or_create(
            comment = comment,
            user    = request.user,
            flag    = comments.models.CommentFlag.MODERATOR_APPROVAL,
        )

        comment.is_removed = False
        comment.is_public = True
        comment.save()

        signals.comment_was_flagged.send(
            sender  = comment.__class__,
            comment = comment,
            flag    = flag,
            created = created,
            request = request,
        )
        return next_redirect(request.POST.copy(), next, approve_done, c=comment.pk)

    # Render a form on GET
    else:
        return render_to_response('comments/approve.html',
            {'comment': comment, "next": next},
            template.RequestContext(request)
        )

approve = permission_required("comments.can_moderate")(approve)


#@permission_required("comments.can_moderate")
def moderation_queue(request):
    """
    Displays a list of unapproved comments to be approved.

    Templates: `comments/moderation_queue.html`
    Context:
        comments
            Comments to be approved (paginated).
        empty
            Is the comment list empty?
        is_paginated
            Is there more than one page?
        results_per_page
            Number of comments per page
        has_next
            Is there a next page?
        has_previous
            Is there a previous page?
        page
            The current page number
        next
            The next page number
        pages
            Number of pages
        hits
            Total number of comments
        page_range
            Range of page numbers

    """
    qs = comments.get_model().objects.filter(is_public=False, is_removed=False)
    paginator = Paginator(qs, 100)

    try:
        page = int(request.GET.get("page", 1))
    except ValueError:
        raise Http404

    try:
        comments_per_page = paginator.page(page)
    except InvalidPage:
        raise Http404

    return render_to_response("comments/moderation_queue.html", {
        'comments' : comments_per_page.object_list,
        'empty' : page == 1 and paginator.count == 0,
        'is_paginated': paginator.num_pages > 1,
        'results_per_page': 100,
        'has_next': comments_per_page.has_next(),
        'has_previous': comments_per_page.has_previous(),
        'page': page,
        'next': page + 1,
        'previous': page - 1,
        'pages': paginator.num_pages,
        'hits' : paginator.count,
        'page_range' : paginator.page_range
    }, context_instance=template.RequestContext(request))

moderation_queue = permission_required("comments.can_moderate")(moderation_queue)

flag_done = confirmation_view(
    template = "comments/flagged.html",
    doc = 'Displays a "comment was flagged" success page.'
)
delete_done = confirmation_view(
    template = "comments/deleted.html",
    doc = 'Displays a "comment was deleted" success page.'
)
approve_done = confirmation_view(
    template = "comments/approved.html",
    doc = 'Displays a "comment was approved" success page.'
)

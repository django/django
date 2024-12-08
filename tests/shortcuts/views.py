from django.shortcuts import render


def render_view(request):
    return render(
        request,
        "shortcuts/render_test.html",
        {
            "foo": "FOO",
            "bar": "BAR",
        },
    )


def render_view_with_multiple_templates(request):
    return render(
        request,
        [
            "shortcuts/no_such_template.html",
            "shortcuts/render_test.html",
        ],
        {
            "foo": "FOO",
            "bar": "BAR",
        },
    )


def render_view_with_content_type(request):
    return render(
        request,
        "shortcuts/render_test.html",
        {
            "foo": "FOO",
            "bar": "BAR",
        },
        content_type="application/x-rendertest",
    )


def render_view_with_status(request):
    return render(
        request,
        "shortcuts/render_test.html",
        {
            "foo": "FOO",
            "bar": "BAR",
        },
        status=403,
    )


def render_view_with_using(request):
    using = request.GET.get("using")
    return render(request, "shortcuts/using.html", using=using)

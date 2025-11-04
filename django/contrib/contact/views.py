from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect

from .forms import ContactForm


@csrf_protect
def contact_view(request):
    """
    Display and process the contact form.

    GET: Display empty contact form
    POST: Process form submission and redirect to thank you page
    """
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("contact:thank_you")
    else:
        form = ContactForm()

    return render(request, "contact/contact_form.html", {"form": form})


def thank_you_view(request):
    """
    Display thank you page after successful form submission.
    """
    return render(request, "contact/thank_you.html")

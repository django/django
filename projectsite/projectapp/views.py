from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse

# Displaying home/index
def index(request):
    # return HttpResponse("Hello, world. You're at the polls index.")
    return render(request, 'index.html')

# Displaying Project Details
def project_detail(request):
    return render(request, 'project_detail.html')

# Displaying Individual Projects
# def p_(request):
#     return render(request, 'p_.html')
def p_ro_website(request):
    return render(request, 'p_ro_website.html')
def p_ro_deal_editor(request):
    return render(request, 'p_ro_deal_editor.html')
def p_codepen_invite(request):
    return render(request, 'p_codepen_invite.html')
def p_codepen_dashboard(request):
    return render(request, 'p_codepen_dashboard.html')
def p_rev_design(request):
    return render(request, 'p_rev_design.html')
def p_rev_email(request):
    return render(request, 'p_rev_email.html')
def p_rev_mktg(request):
    return render(request, 'p_rev_mktg.html')
def p_print(request):
    return render(request, 'p_print.html')
def p_portfolio(request):
    return render(request, 'p_portfolio.html')

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

# Displaying Email Strategy
def p_email_strategy(request):
    return render(request, 'p_email_strategy.html')

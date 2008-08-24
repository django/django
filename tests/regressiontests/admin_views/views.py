from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse

def secure_view(request):
    return HttpResponse('%s' % request.POST)
secure_view = staff_member_required(secure_view)
from freedom.contrib.admin.views.decorators import staff_member_required
from freedom.http import HttpResponse


@staff_member_required
def secure_view(request):
    return HttpResponse('%s' % request.POST)

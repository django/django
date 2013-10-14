from django.http import HttpResponse


def custom_submit_comment(request):
    return HttpResponse("Hello from the custom submit comment view.")

def custom_flag_comment(request, comment_id):
    return HttpResponse("Hello from the custom flag view.")

def custom_delete_comment(request, comment_id):
    return HttpResponse("Hello from the custom delete view.")

def custom_approve_comment(request, comment_id):
    return HttpResponse("Hello from the custom approve view.")

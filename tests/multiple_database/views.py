from django.http import HttpResponse

from .models import Book


def book(request, book_id):
    b = Book.objects.get(id=book_id)
    return HttpResponse(b.title)

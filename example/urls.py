from django.conf.urls.defaults import *

from cube.views import table_from_cube

from example.bookcase.models import Book, BookCaseCube

urlpatterns = patterns('',
    url(r'^$', table_from_cube, kwargs={
        'cube': BookCaseCube(Book.objects.all()),
        'dimensions': ['genre', 'first_letter_title'],
    }),
)

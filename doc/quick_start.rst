Quick start
############

Install django-cube
=====================

Put `cube` somewhere in your Python path, then put cube in `INSTALLED_APPS` in your settings ::

    INSTALLED_APPS = (
        #your other apps ...
        'cube',
    )

Set-up your cube
==================

You have some django models like this one (don't forget to sync your database...) ::

    from django.db import models

    class Book (models.Model):
        title = models.CharField(max_length=100)
        genre = models.CharField(max_length=100)

Then, anywhere in your project, just create a cube based on this model ::

    from cube.models import Cube, Dimension

    class BookCaseCube(Cube):

        genre = Dimension('genre')
        first_letter_title = Dimension('title__iregex', sample_space=[r'^[a-n]', r'^[m-z]'])

        @staticmethod
        def aggregation(queryset):
            return queryset.count()

This cube is defined with 2 dimensions :

    - **genre** : the genre of the book. Relates to the field named `genre` on the model.
    - **first_letter_title** : the first letter of book's title. Relates to the field `title`, with the field-lookup `iregex`, and specifies the `sample_space` of the dimension, i.e. the list of values this dimension can take.

, and one aggregation which is in fact a simple `COUNT`.

Display a nice table
=====================

Now that your cube is set-up, one use-case of django-cube is to render a table of measures.

This can be very easily done by using the view :func:`table_from_cube`. In your urls, just write ::

    from cube.views import table_from_cube

    from example.bookcase.models import Book, BookCaseCube

    urlpatterns = patterns('',
        url(r'^$', table_from_cube, kwargs={
            'cube': BookCaseCube(Book.objects.all()),
            'dimensions': ['genre', 'first_letter_title'],
        }),
    )

And you're done !

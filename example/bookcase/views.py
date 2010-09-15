# cube declaration
from cube.models import Cube, Dimension

class BookCaseCube(Cube):

    genre = Dimension('genre')
    first_letter_title = Dimension('title__iregex', sample_space=[r'^[a-n]', r'^[m-z]'])

    @staticmethod
    def aggregation(queryset):
        return queryset.count()

# views declaration
from example.bookcase.models import Book
from cube.views import table_from_cube

def books_count(request):
    cube = BookCaseCube(Book.objects.all())
    return table_from_cube(request, cube, ['genre', 'first_letter_title'], template='table.html')

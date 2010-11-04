"""
.. 
    >>> from datetime import datetime, date
    >>> from cube.models import Cube, Dimension
    >>> from cube.views import table_from_cube
    >>> import copy

.. currentmodule:: cube

Some fixtures for the examples ...

Some models

    >>> class Instrument(models.Model):
    ...     name = models.CharField(max_length=100)
    ... 
    >>> class Musician(models.Model):
    ...     firstname = models.CharField(max_length=100)
    ...     lastname = models.CharField(max_length=100)
    ...     instrument = models.ForeignKey(Instrument)
    ... 
    >>> class Song(models.Model):
    ...     title = models.CharField(max_length=100)
    ...     release_date = models.DateField()
    ...     author = models.ForeignKey(Musician)
    ... 

Some instruments

    >>> trumpet = Instrument(name='trumpet')
    >>> piano = Instrument(name='piano')
    >>> sax = Instrument(name='sax')

..
    >>> trumpet.save() ; piano.save() ; sax.save()

Some musicians

    >>> miles_davis = Musician(firstname='Miles', lastname='Davis', instrument=trumpet)
    >>> freddie_hubbard = Musician(firstname='Freddie', lastname='Hubbard', instrument=trumpet)
    >>> erroll_garner = Musician(firstname='Erroll', lastname='Garner', instrument=piano)
    >>> bill_evans_p = Musician(firstname='Bill', lastname='Evans', instrument=piano)
    >>> thelonious_monk = Musician(firstname='Thelonious', lastname='Monk', instrument=piano)
    >>> bill_evans_s = Musician(firstname='Bill', lastname='Evans', instrument=sax)

..
    >>> miles_davis.save() ; freddie_hubbard.save() ; erroll_garner.save() ; bill_evans_p.save() ; thelonious_monk.save() ; bill_evans_s.save()

Some songs

    >>> so_what = Song(title='So What', author=miles_davis, release_date=date(1959, 8, 17))
    >>> all_blues = Song(title='All Blues', author=miles_davis, release_date=date(1959, 8, 17))
    >>> blue_in_green = Song(title='Blue In Green', author=bill_evans_p, release_date=date(1959, 8, 17))
    >>> south_street_stroll = Song(title='South Street Stroll', author=freddie_hubbard, release_date=date(1969, 1, 21))
    >>> well_you_neednt = Song(title='Well You Needn\\'t', author=thelonious_monk, release_date=date(1944, 2, 1))
    >>> blue_monk = Song(title='Blue Monk', author=thelonious_monk, release_date=date(1945, 2, 1))

..
    >>> so_what.save() ; all_blues.save() ; blue_in_green.save() ; south_street_stroll.save() ; well_you_neednt.save() ; blue_monk.save()


Dimension
===========
..
    ----- Deep copy
    >>> d = Dimension(field='attribute__date__absmonth', queryset=[1, 2, 3], sample_space=[89, 99])
    >>> d_copy = copy.deepcopy(d)

    >>> id(d_copy) != id(d)
    True
    >>> d_copy.field == d.field
    True
    >>> id(d_copy.sample_space) != id(d.sample_space) ; d_copy.sample_space == d.sample_space
    True
    True
    >>> id(d_copy.queryset) != id(d.queryset) ; d_copy.queryset == d.queryset
    True
    True

    ----- Formatting datetimes constraint
    >>> d = Dimension(field='attribute__date__absmonth')
    >>> d.constraint = date(3000, 7, 1)
    >>> d.to_queryset_filter() == {'attribute__date__month': 7, 'attribute__date__year': 3000}
    True
    >>> d = Dimension(field='attribute__date__absday')
    >>> d.constraint = datetime(1990, 8, 23, 0, 0, 0)
    >>> d.to_queryset_filter() == {'attribute__date__day': 23, 'attribute__date__month': 8, 'attribute__date__year': 1990}
    True
    >>> d = Dimension()
    >>> d._name = 'myname'
    >>> d.constraint = 'coucou'
    >>> d.to_queryset_filter() == {'myname': 'coucou'}
    True

Setting a dimension's sample space
---------------------------------------

You can set explicitely the sample space for a dimension, by passing to the constructor a keyword *sample_space* that is an iterable. It works with lists :

    >>> d = Dimension(field='instrument__name', sample_space=['trumpet', 'piano'])
    >>> d.get_sample_space(sort=True) == sorted(['trumpet', 'piano'])
    True

But also with querysets (any iterable):

    >>> d = Dimension(field='instrument', sample_space=Instrument.objects.filter(name__contains='a').order_by('name'))
    >>> d.get_sample_space() == [piano, sax]
    True

Default sample space for a dimension
-----------------------------------------------

If you didn't give explicitely the sample space of a dimension, the method :meth:`get_sample_space` will return a default sample space taken from the dimension's queryset.

    >>> d = Dimension(field='title', queryset=Song.objects.all())
    >>> set(d.get_sample_space()) == set([
    ...     'So What', 'All Blues', 'Blue In Green',
    ...     'South Street Stroll', 'Well You Needn\\'t', 'Blue Monk'
    ... ])
    True

It works also with field names that use django field-lookup syntax

    >>> d = Dimension(field='release_date__year', queryset=Song.objects.all())
    >>> d.get_sample_space() == sorted([1944, 1969, 1959, 1945])
    True

And you can also use the special "field-lookups" *absmonth* or *absday*

    >>> d = Dimension(field='release_date__absmonth', queryset=Song.objects.all())
    >>> d.get_sample_space() == sorted([
    ...     datetime(1969, 1, 1, 0, 0), datetime(1945, 2, 1, 0, 0),
    ...     datetime(1944, 2, 1, 0, 0), datetime(1959, 8, 1, 0, 0)
    ... ])
    True
    >>> d = Dimension(field='release_date__absday', queryset=Song.objects.all())
    >>> d.get_sample_space() == sorted([
    ...     datetime(1969, 1, 21, 0, 0), datetime(1945, 2, 1, 0, 0),
    ...     datetime(1944, 2, 1, 0, 0), datetime(1959, 8, 17, 0, 0)
    ... ])
    True

You can traverse foreign keys,

    >>> d = Dimension(field='author__firstname', queryset=Song.objects.all())
    >>> d.get_sample_space(sort=True) == sorted(['Bill', 'Miles', 'Thelonious', 'Freddie'])
    True
    >>> d = Dimension(field='author__instrument__name', queryset=Song.objects.all())
    >>> d.get_sample_space(sort=True) == sorted(['piano', 'trumpet'])
    True

and refer to any type of field, even a django object

    >>> d = Dimension(field='author__instrument', queryset=Song.objects.all())
    >>> d.get_sample_space(sort=True) == [trumpet, piano] # django objects are ordered by their pk
    True
    >>> d = Dimension(field='author', queryset=Song.objects.all())
    >>> d.get_sample_space(sort=True) == [
    ...     miles_davis, freddie_hubbard,
    ...     bill_evans_p, thelonious_monk,
    ... ]
    True

Giving dimension's sample space as a callable
---------------------------------------------

You can pass a callable to the dimension's constructor to set its sample space. This callable takes a queryset as parameter, and returns the sample space. For example :

    >>> def select_contains_s(queryset):
    ...     #This function returns all musicians that wrote a song
    ...     #and whose last name contains at least one 's'
    ...     s_queryset = queryset.filter(author__lastname__icontains='s').distinct().select_related()
    ...     m_queryset = Musician.objects.filter(pk__in=s_queryset.values_list('author', flat=True))
    ...     return list(m_queryset)
    >>> d = Dimension(field='author', queryset=Song.objects.all(), sample_space=select_contains_s)
    >>> d.get_sample_space() == [
    ...     miles_davis, bill_evans_p
    ... ]
    True

Overriding the display of dimension's value
---------------------------------------------

:class:`Dimension` provides a property :meth:`Dimension.pretty_constraint` which gives a pretty version of the dimension's value (AKA its constraint). To customize this display, just declare a new sub-class of :class:`Dimension`, and override the :meth:`pretty_constraint` property. For example, this displays an Instrument object as its name, with a capital letter first :

    >>> class InstrumentDimension(Dimension):
    ...     @property
    ...     def pretty_constraint(self):
    ...         return self.constraint.name.capitalize()

Cube
======

..
    Metaclass
    -----------
    >>> class MyCube(Cube):
    ...     dim1 = Dimension()
    ...     dim2 = Dimension()
    >>> set([dim.name for dim in MyCube._meta.dimensions.values()]) == set(['dim1', 'dim2'])
    True

    Inheritance
    --------------
    >>> class ParentCube(Cube):
    ...     dim1 = Dimension()
    ...     dim2 = Dimension()
    >>> class ChildCube(ParentCube):
    ...     pass
    >>> set([dim.name for dim in ChildCube._meta.dimensions.values()]) == set(['dim1', 'dim2'])
    True
    >>> set(ChildCube._meta.dimensions.values()) == set(ParentCube._meta.dimensions.values())
    False


Declaring cubes 
-----------------

Declaring a cube is very similar to declaring a Django model, with dimensions instead of fields. Notice that you have to override the static method :meth:`aggregation`, which calculates the aggregation on a given queryset.

    >>> class SongCube(Cube):
    ...     author = Dimension()
    ...     auth_name = Dimension(field='author__lastname')
    ...     date = Dimension(field='release_date')
    ...     date_absmonth = Dimension(field='release_date__absmonth')
    ...     date_month = Dimension(field='release_date__month')
    ...     date_year = Dimension(field='release_date__year')
    ...     
    ...     @staticmethod
    ...     def aggregation(queryset):
    ...         return queryset.count()
    ... 
    >>> class MusicianCube(Cube):
    ...     instrument_name = Dimension(field='instrument__name')
    ...     instrument_cat = Dimension(field='instrument__name__in',
    ...         sample_space=[('trumpet', 'piano'), ('trumpet', 'sax'), ('sax', 'piano')])
    ...     instrument = InstrumentDimension()
    ...     firstname = Dimension()
    ...     lastname = Dimension()
    ...     
    ...     @staticmethod
    ...     def aggregation(queryset):
    ...         return queryset.count()

.. 
    ----- Deep copy
    >>> c = MusicianCube(Musician.objects.all())
    >>> c_copy = copy.deepcopy(c)
    >>> id(c_copy) != id(c)
    True
    >>> set(c_copy.dimensions.keys()) == set(c.dimensions.keys())
    True
    >>> c_copy.constraint == c.constraint
    True
    >>> id(c_copy.queryset) != id(c.queryset) ; list(c_copy.queryset) == list(c.queryset)
    True
    True

Get a cube's sample space
----------------------------

On the cube, you can get the sample space for one dimension like this :
    
    >>> c.get_sample_space('firstname', format='flat') == ['Bill', 'Erroll', 'Freddie', 'Miles', 'Thelonious']
    True
    
and the cube's sample space for several dimensions like this :
    
    >>> c.get_sample_space('firstname', 'instrument_name') == [
    ...     {'firstname': 'Bill', 'instrument_name': 'piano'},
    ...     {'firstname': 'Bill', 'instrument_name': 'sax'},
    ...     {'firstname': 'Bill', 'instrument_name': 'trumpet'},
    ...     {'firstname': 'Erroll', 'instrument_name': 'piano'},
    ...     {'firstname': 'Erroll', 'instrument_name': 'sax'},
    ...     {'firstname': 'Erroll', 'instrument_name': 'trumpet'},
    ...     {'firstname': 'Freddie', 'instrument_name': 'piano'},
    ...     {'firstname': 'Freddie', 'instrument_name': 'sax'},
    ...     {'firstname': 'Freddie', 'instrument_name': 'trumpet'},
    ...     {'firstname': 'Miles', 'instrument_name': 'piano'},
    ...     {'firstname': 'Miles', 'instrument_name': 'sax'},
    ...     {'firstname': 'Miles', 'instrument_name': 'trumpet'},
    ...     {'firstname': 'Thelonious', 'instrument_name': 'piano'},
    ...     {'firstname': 'Thelonious', 'instrument_name': 'sax'},
    ...     {'firstname': 'Thelonious', 'instrument_name': 'trumpet'},
    ... ]
    True

And note that if one dimension is already constrained, the sample space for the cube on this dimension is the constraint value :
    
    >>> c = c.constrain(firstname='Bill')
    >>> c.get_sample_space('firstname', 'instrument_name') == [
    ...     {'firstname': 'Bill', 'instrument_name': 'piano'},
    ...     {'firstname': 'Bill', 'instrument_name': 'sax'},
    ...     {'firstname': 'Bill', 'instrument_name': 'trumpet'},
    ... ]
    True

Getting a measure from the cube
--------------------------------

Once you have instantiated a cube with a base queryset, you can access a measure at any valid coordinates. 

    >>> c = MusicianCube(Musician.objects.all())
    >>> c.measure(firstname='Miles')
    1
    >>> c.measure(firstname='Bill')
    2
    >>> c.measure(firstname='Miles', instrument_name='trumpet')
    1
    >>> c.measure(firstname='Miles', instrument_name='piano')
    0
    >>> c.measure()
    6

Iterating over cube's subcubes
---------------------------------

If your cube has no constrained dimension, querying its subcubes will yield as many subcubes as there are combinations of elements from the dimensions' sample spaces. For example : 
    >>> ['%s' % subcube for subcube in c.subcubes('firstname', 'instrument_name')] == [
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Bill, instrument_name=piano)',
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Bill, instrument_name=sax)',
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Bill, instrument_name=trumpet)',
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Erroll, instrument_name=piano)',
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Erroll, instrument_name=sax)',
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Erroll, instrument_name=trumpet)',
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Freddie, instrument_name=piano)',
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Freddie, instrument_name=sax)',
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Freddie, instrument_name=trumpet)',
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Miles, instrument_name=piano)',
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Miles, instrument_name=sax)',
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Miles, instrument_name=trumpet)',
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Thelonious, instrument_name=piano)',
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Thelonious, instrument_name=sax)',
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Thelonious, instrument_name=trumpet)'
    ... ]
    True

On the other hand, if your cube is constrained, all the subcubes yielded will be constrained as well : 

    >>> c = MusicianCube(Musician.objects.all()).constrain(firstname='Miles')
    >>> ['%s' % subcube for subcube in c.subcubes('firstname')] == [
    ...     'Cube(instrument, instrument_cat, instrument_name, lastname, firstname=Miles)',
    ... ]
    True

List of measures as dictionnaries
----------------------------------

Using :meth:`Cube.measures`, you can get a list of measures, very similar to what is returned by the `.values()` method on a django queryset.

    >>> c = MusicianCube(Musician.objects.filter(instrument__name__in=['piano', 'trumpet']))
    >>> c.measures('firstname', 'instrument_name') == [
    ...     {'firstname': 'Bill', 'instrument_name': 'piano', '__measure': 1},
    ...     {'firstname': 'Bill', 'instrument_name': 'trumpet', '__measure': 0},
    ...     {'firstname': 'Erroll', 'instrument_name': 'piano', '__measure': 1},
    ...     {'firstname': 'Erroll', 'instrument_name': 'trumpet', '__measure': 0},
    ...     {'firstname': 'Freddie', 'instrument_name': 'piano', '__measure': 0},
    ...     {'firstname': 'Freddie', 'instrument_name': 'trumpet', '__measure': 1},
    ...     {'firstname': 'Miles', 'instrument_name': 'piano', '__measure': 0},
    ...     {'firstname': 'Miles', 'instrument_name': 'trumpet', '__measure': 1},
    ...     {'firstname': 'Thelonious', 'instrument_name': 'piano', '__measure': 1},
    ...     {'firstname': 'Thelonious', 'instrument_name': 'trumpet', '__measure': 0},
    ... ]
    True

Multidimensionnal dictionnary of measures
-------------------------------------------

Using :meth:`Cube.measures_dict`, you can get a dictionnary of all the measures, organized by dimensions : 

    >>> c = MusicianCube(Musician.objects.filter(instrument__name__in=['piano', 'trumpet']))
    >>> c.measures_dict('firstname', 'instrument_name') == {
    ...     'subcubes': {
    ...         'Bill': {
    ...             'subcubes': {
    ...                 'piano': {'measure': 1},
    ...                 'trumpet': {'measure': 0},
    ...             },
    ...             'measure': 1
    ...         },
    ...         'Miles': {
    ...             'subcubes': {
    ...                 'piano': {'measure': 0},
    ...                 'trumpet': {'measure': 1},
    ...             },
    ...             'measure': 1
    ...         },
    ...         'Thelonious': {
    ...             'subcubes': {
    ...                 'piano': {'measure': 1},
    ...                 'trumpet': {'measure': 0},
    ...             },
    ...             'measure': 1
    ...         },
    ...         'Freddie': {
    ...             'subcubes': {
    ...                 'piano': {'measure': 0},
    ...                 'trumpet': {'measure': 1},
    ...             },
    ...             'measure': 1
    ...         },
    ...         'Erroll': {
    ...             'subcubes': {
    ...                 'piano': {'measure': 1},
    ...                 'trumpet': {'measure': 0},
    ...             },
    ...             'measure': 1
    ...         },
    ...     },
    ...     'measure': 5
    ... }
    True

You can do the same thing, but calculating only the measures for the subcubes whose dimensions passed to :meth:`measures_dict` are all fixed.

    >>> c.measures_dict('firstname', 'instrument_name', full=False) == {
    ...     'Bill': {
    ...         'piano': {'measure': 1},
    ...         'trumpet': {'measure': 0},
    ...     },
    ...     'Miles': {
    ...         'piano': {'measure': 0},
    ...         'trumpet': {'measure': 1},
    ...     },
    ...     'Thelonious': {
    ...         'piano': {'measure': 1},
    ...         'trumpet': {'measure': 0},
    ...     },
    ...     'Freddie': {
    ...         'piano': {'measure': 0},
    ...         'trumpet': {'measure': 1},
    ...     },
    ...     'Erroll': {
    ...         'piano': {'measure': 1},
    ...         'trumpet': {'measure': 0},
    ...     },
    ... }
    True

Multidimensionnal list of measures
------------------------------------

Using :meth:`Cube.measures_list`, you can get a list of measures organized by dimension :

    >>> c.measures_list('firstname', 'instrument_name') == [
    ...     [1, 0], #Bill: piano, trumpet
    ...     [1, 0], #Erroll ...
    ...     [0, 1], #Freddie ...
    ...     [0, 1], #Miles ...
    ...     [1, 0], #Thelonious ...
    ... ]
    True
    >>> other_c = MusicianCube(Musician.objects.filter(instrument__name__in=['piano']))
    >>> other_c.measures_list('firstname', 'instrument_name', 'lastname') == [
    ...     [[1, 0, 0]], #Bill: piano: Evans, Garner, Monk
    ...     [[0, 1, 0]], #Erroll ...
    ...     [[0, 0, 1]], #Thelonious ...
    ... ]
    True

Getting a subcube
------------------

You can get a subcube of a cube by constraining it :

    >>> subcube = c.constrain(instrument_name='trumpet')
    >>> subcube.measures_dict('firstname', 'instrument_name', full=False) == {
    ...     'Bill': {
    ...         'trumpet': {'measure': 0},
    ...     },
    ...     'Erroll': {
    ...         'trumpet': {'measure': 0},
    ...     },
    ...     'Freddie': {
    ...         'trumpet': {'measure': 1},
    ...     },
    ...     'Miles': {
    ...         'trumpet': {'measure': 1},
    ...     },
    ...     'Thelonious': {
    ...         'trumpet': {'measure': 0},
    ...     },
    ... }
    True

Using Django field-lookup syntax for date dimensions (see the dimensions declaration) works pretty well too :

    >>> c = SongCube(Song.objects.all())
    >>> subcube = c.constrain(date_month=2)
    >>> subcube.measures_dict('date_month', 'date_year', 'auth_name', full=False) == {
    ...     2: {
    ...         1945: {
    ...             'Davis': {'measure': 0},
    ...             'Hubbard': {'measure': 0},
    ...             'Evans': {'measure': 0},
    ...             'Monk': {'measure': 1}
    ...         },
    ...         1944: {
    ...             'Davis': {'measure': 0},
    ...             'Hubbard': {'measure': 0},
    ...             'Evans': {'measure': 0},
    ...             'Monk': {'measure': 1}
    ...         },
    ...         1969: {
    ...             'Davis': {'measure': 0},
    ...             'Hubbard': {'measure': 0},
    ...             'Evans': {'measure': 0},
    ...             'Monk': {'measure': 0}
    ...         },
    ...         1959: {
    ...             'Davis': {'measure': 0},
    ...             'Hubbard': {'measure': 0},
    ...             'Evans': {'measure': 0},
    ...             'Monk': {'measure': 0}
    ...         },
    ...     }
    ... }
    True

As well as using Django field-lookup syntax for relations (see the dimensions declaration) :

    >>> c = MusicianCube(Musician.objects.all())
    >>> c.measures_dict('instrument_cat', 'firstname', full=False) == {
    ...     ('trumpet', 'piano'): {
    ...         'Bill': {'measure': 1},
    ...         'Erroll': {'measure': 1},
    ...         'Miles': {'measure': 1},
    ...         'Freddie': {'measure': 1},
    ...         'Thelonious': {'measure': 1},
    ...     },
    ...     ('trumpet', 'sax'): {
    ...         'Bill': {'measure': 1},
    ...         'Erroll': {'measure': 0},
    ...         'Miles': {'measure': 1},
    ...         'Freddie': {'measure': 1},
    ...         'Thelonious': {'measure': 0},
    ...     },
    ...     ('sax', 'piano'): {
    ...         'Bill': {'measure': 2},
    ...         'Erroll': {'measure': 1},
    ...         'Miles': {'measure': 0},
    ...         'Freddie': {'measure': 0},
    ...         'Thelonious': {'measure': 1},
    ...     },
    ... }
    True

Sorting results
---------------------
We declare a cube that overrides *sort_key* to provide custom sorting.

    >>> class SortedCube(Cube):
    ...     instrument_name = Dimension(field='instrument__name')
    ...     firstname = Dimension()
    ...     lastname = Dimension()
    ...     
    ...     @staticmethod
    ...     def sort_key(coordinates):
    ...         coordinates = dict(coordinates)
    ...         if coordinates.get('firstname'):
    ...             return coordinates.pop('firstname') + ''.join(coordinates.values())
    ...
    ...     @staticmethod
    ...     def aggregation(queryset):
    ...         return queryset.count()

Now, everytime that the dimension *firstname* is used, it has priority on other dimensions for sorting.

    >>> ['%s' % c for c in SortedCube(Musician.objects.all()).subcubes('instrument_name', 'firstname')] == [
    ...     u'Cube(lastname, firstname=Bill, instrument_name=piano)',
    ...     u'Cube(lastname, firstname=Bill, instrument_name=sax)',
    ...     u'Cube(lastname, firstname=Bill, instrument_name=trumpet)',
    ...     u'Cube(lastname, firstname=Erroll, instrument_name=piano)',
    ...     u'Cube(lastname, firstname=Erroll, instrument_name=sax)',
    ...     u'Cube(lastname, firstname=Erroll, instrument_name=trumpet)',
    ...     u'Cube(lastname, firstname=Freddie, instrument_name=piano)',
    ...     u'Cube(lastname, firstname=Freddie, instrument_name=sax)',
    ...     u'Cube(lastname, firstname=Freddie, instrument_name=trumpet)',
    ...     u'Cube(lastname, firstname=Miles, instrument_name=piano)',
    ...     u'Cube(lastname, firstname=Miles, instrument_name=sax)',
    ...     u'Cube(lastname, firstname=Miles, instrument_name=trumpet)',
    ...     u'Cube(lastname, firstname=Thelonious, instrument_name=piano)',
    ...     u'Cube(lastname, firstname=Thelonious, instrument_name=sax)',
    ...     u'Cube(lastname, firstname=Thelonious, instrument_name=trumpet)'
    ... ]
    True

    >>> ['%s' % c for c in SortedCube(Musician.objects.all()).subcubes('firstname', 'instrument_name')] == [
    ...     u'Cube(lastname, firstname=Bill, instrument_name=piano)',
    ...     u'Cube(lastname, firstname=Bill, instrument_name=sax)',
    ...     u'Cube(lastname, firstname=Bill, instrument_name=trumpet)',
    ...     u'Cube(lastname, firstname=Erroll, instrument_name=piano)',
    ...     u'Cube(lastname, firstname=Erroll, instrument_name=sax)',
    ...     u'Cube(lastname, firstname=Erroll, instrument_name=trumpet)',
    ...     u'Cube(lastname, firstname=Freddie, instrument_name=piano)',
    ...     u'Cube(lastname, firstname=Freddie, instrument_name=sax)',
    ...     u'Cube(lastname, firstname=Freddie, instrument_name=trumpet)',
    ...     u'Cube(lastname, firstname=Miles, instrument_name=piano)',
    ...     u'Cube(lastname, firstname=Miles, instrument_name=sax)',
    ...     u'Cube(lastname, firstname=Miles, instrument_name=trumpet)',
    ...     u'Cube(lastname, firstname=Thelonious, instrument_name=piano)',
    ...     u'Cube(lastname, firstname=Thelonious, instrument_name=sax)',
    ...     u'Cube(lastname, firstname=Thelonious, instrument_name=trumpet)'
    ... ]
    True
    

Template tags and filters
============================
..
    >>> from cube.templatetags import cube_templatetags
    >>> from django.template import Template, Context, Variable
    >>> import re

Iterating over cube's subcubes
-------------------------------

Let's create a cube

    >>> c = MusicianCube(Musician.objects.filter(firstname__in=['Bill', 'Miles']))

Here's how to use the template tag *subcubes* to iterate over subcubes :

    >>> context = Context({'my_cube': c, 'dim1': 'firstname'})
    >>> template = Template(
    ...     '{% load cube_templatetags %}'
    ...     '{% subcubes my_cube by dim1, "instrument_name" as subcube1 %}'
    ...         '{{ subcube1 }}:{{ subcube1.measure }}'
    ...         '{% subcubes subcube1 by "lastname" as subcube2 %}'
    ...             '{{ subcube2 }}:{{ subcube2.measure }}'
    ...         '{% endsubcubes %}'
    ...     '{% endsubcubes %}'
    ... )

Here is what the rendering gives :

    >>> awaited = ''\\
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Bill, instrument_name=piano):1'\\
    ...         'Cube(instrument, instrument_cat, firstname=Bill, instrument_name=piano, lastname=Davis):0'\\
    ...         'Cube(instrument, instrument_cat, firstname=Bill, instrument_name=piano, lastname=Evans):1'\\
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Bill, instrument_name=sax):1'\\
    ...         'Cube(instrument, instrument_cat, firstname=Bill, instrument_name=sax, lastname=Davis):0'\\
    ...         'Cube(instrument, instrument_cat, firstname=Bill, instrument_name=sax, lastname=Evans):1'\\
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Bill, instrument_name=trumpet):0'\\
    ...         'Cube(instrument, instrument_cat, firstname=Bill, instrument_name=trumpet, lastname=Davis):0'\\
    ...         'Cube(instrument, instrument_cat, firstname=Bill, instrument_name=trumpet, lastname=Evans):0'\\
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Miles, instrument_name=piano):0'\\
    ...         'Cube(instrument, instrument_cat, firstname=Miles, instrument_name=piano, lastname=Davis):0'\\
    ...         'Cube(instrument, instrument_cat, firstname=Miles, instrument_name=piano, lastname=Evans):0'\\
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Miles, instrument_name=sax):0'\\
    ...         'Cube(instrument, instrument_cat, firstname=Miles, instrument_name=sax, lastname=Davis):0'\\
    ...         'Cube(instrument, instrument_cat, firstname=Miles, instrument_name=sax, lastname=Evans):0'\\
    ...     'Cube(instrument, instrument_cat, lastname, firstname=Miles, instrument_name=trumpet):1'\\
    ...         'Cube(instrument, instrument_cat, firstname=Miles, instrument_name=trumpet, lastname=Davis):1'\\
    ...         'Cube(instrument, instrument_cat, firstname=Miles, instrument_name=trumpet, lastname=Evans):0'\\

..
    >>> awaited == template.render(context)
    True


Get a pretty display of a dimension's constraint
----------------------------------------------------

In your templates, you can access the pretty value of dimension's constraint by using the filter `prettyconstraint`. This will call the method :meth:`Dimension.pretty_constraint` on the dimension whose name is passed as argument.

    >>> c = MusicianCube(Musician.objects.all()).constrain(
    ...     firstname='John',
    ...     instrument=sax,
    ... )
    >>> context = Context({'my_cube': c})
    >>> template = Template(
    ... '{% load cube_templatetags %}'
    ... '>FUNKY<{{ my_cube|prettyconstraint:\\'instrument\\' }}>FUNKY<'
    ... )
    >>> template.render(context)
    u'>FUNKY<Sax>FUNKY<'

..

    ----- Test creation of table from cube context
    >>> c = MusicianCube(Musician.objects.all())

    >>> c.table_helper('firstname', 'instrument') == {
    ...     'col_names': [
    ...         ('Bill', 'Bill'),
    ...         ('Erroll', 'Erroll'),
    ...         ('Freddie', 'Freddie'),
    ...         ('Miles', 'Miles'),
    ...         ('Thelonious', 'Thelonious'),
    ...     ],
    ...     'cols': [
    ...         {'name': 'Bill', 'pretty_name': 'Bill', 'values': [0, 1, 1], 'overall': 2},
    ...         {'name': 'Erroll', 'pretty_name': 'Erroll', 'values': [0, 1, 0], 'overall': 1},
    ...         {'name': 'Freddie', 'pretty_name': 'Freddie', 'values': [1, 0, 0], 'overall': 1},
    ...         {'name': 'Miles', 'pretty_name': 'Miles', 'values': [1, 0, 0], 'overall': 1},
    ...         {'name': 'Thelonious', 'pretty_name': 'Thelonious', 'values': [0, 1, 0], 'overall': 1}
    ...     ],
    ...     'col_overalls': [2, 1, 1, 1, 1],
    ...     'row_names': [
    ...         (trumpet, 'Trumpet'),
    ...         (piano, 'Piano'),
    ...         (sax, 'Sax'),
    ...     ],
    ...     'rows': [
    ...         {'name': trumpet, 'pretty_name': 'Trumpet', 'values': [0, 0, 1, 1, 0], 'overall': 2},
    ...         {'name': piano, 'pretty_name': 'Piano', 'values': [1, 1, 0, 0, 1], 'overall': 3},
    ...         {'name': sax, 'pretty_name': 'Sax', 'values': [1, 0, 0, 0, 0], 'overall': 1},
    ...     ],
    ...     'row_overalls': [2, 3, 1],
    ...     'col_dim_name': 'firstname',
    ...     'row_dim_name': 'instrument',
    ...     'overall': 6,
    ... }
    True


Insert a table
----------------

Let's create a cube

    >>> c = MusicianCube(Musician.objects.all())

Here's how to use the inclusion tag *tablefromcube* to insert a table in your template :

    >>> context = Context({'my_cube': c, 'dim1': 'firstname', 'template_name': 'table_from_cube.html'})
    >>> template = Template(
    ... '{% load cube_templatetags %}'
    ... '{% tablefromcube my_cube by dim1, "instrument_name" using template_name %}'
    ... )

It will render 'template_name' with a context built from :meth:`models.Cube.table_helper`.

Here is what the rendering gives :

    >>> awaited = ''\\
    ... '<table>'\\
    ...     '<theader>'\\
    ...         '<tr>'\\
    ...             '<th></th>'\\
    ...             '<th>Bill</th>'\\
    ...             '<th>Erroll</th>'\\
    ...             '<th>Freddie</th>'\\
    ...             '<th>Miles</th>'\\
    ...             '<th>Thelonious</th>'\\
    ...             '<th>OVERALL</th>'\\
    ...         '</tr>'\\
    ...     '</theader>'\\
    ...     '<tbody>'\\
    ...         '<tr>'\\
    ...             '<th>piano</th>'\\
    ...             '<td>1</td>'\\
    ...             '<td>1</td>'\\
    ...             '<td>0</td>'\\
    ...             '<td>0</td>'\\
    ...             '<td>1</td>'\\
    ...             '<td>3</td>'\\
    ...         '</tr>'\\
    ...         '<tr>'\\
    ...             '<th>sax</th>'\\
    ...             '<td>1</td>'\\
    ...             '<td>0</td>'\\
    ...             '<td>0</td>'\\
    ...             '<td>0</td>'\\
    ...             '<td>0</td>'\\
    ...             '<td>1</td>'\\
    ...         '</tr>'\\
    ...         '<tr>'\\
    ...             '<th>trumpet</th>'\\
    ...             '<td>0</td>'\\
    ...             '<td>0</td>'\\
    ...             '<td>1</td>'\\
    ...             '<td>1</td>'\\
    ...             '<td>0</td>'\\
    ...             '<td>2</td>'\\
    ...         '</tr>'\\
    ...     '</tbody>'\\
    ...     '<tfoot>'\\
    ...         '<tr>'\\
    ...             '<th>OVERALL</th>'\\
    ...             '<td>2</td>'\\
    ...             '<td>1</td>'\\
    ...             '<td>1</td>'\\
    ...             '<td>1</td>'\\
    ...             '<td>1</td>'\\
    ...             '<td>6</td>'\\
    ...         '</tr>'\\
    ...     '</tfoot>'\\
    ... '</table>'

..
    >>> awaited == re.sub(' |\\n', '', template.render(context))
    True

Views
=======

Get a table from a cube
-------------------------

Let's create a cube

    >>> c = MusicianCube(Musician.objects.all())

..
    >>> from django.http import HttpRequest
    >>> request = HttpRequest()

Let's use the view :func:`views.table_from_cube` which will render the template with a context built from :meth:`models.Cube.table_helper`. :
    
    >>> response = table_from_cube(request, cube=c, dimensions=['firstname', 'instrument_name'])
    
Here is what the rendering gives :

    >>> awaited = ''\\
    ... 'Content-Type:text/html;charset=utf-8'\\
    ... '<table>'\\
    ...     '<theader>'\\
    ...         '<tr>'\\
    ...             '<th></th>'\\
    ...             '<th>Bill</th>'\\
    ...             '<th>Erroll</th>'\\
    ...             '<th>Freddie</th>'\\
    ...             '<th>Miles</th>'\\
    ...             '<th>Thelonious</th>'\\
    ...             '<th>OVERALL</th>'\\
    ...         '</tr>'\\
    ...     '</theader>'\\
    ...     '<tbody>'\\
    ...         '<tr>'\\
    ...             '<th>piano</th>'\\
    ...             '<td>1</td>'\\
    ...             '<td>1</td>'\\
    ...             '<td>0</td>'\\
    ...             '<td>0</td>'\\
    ...             '<td>1</td>'\\
    ...             '<td>3</td>'\\
    ...         '</tr>'\\
    ...         '<tr>'\\
    ...             '<th>sax</th>'\\
    ...             '<td>1</td>'\\
    ...             '<td>0</td>'\\
    ...             '<td>0</td>'\\
    ...             '<td>0</td>'\\
    ...             '<td>0</td>'\\
    ...             '<td>1</td>'\\
    ...         '</tr>'\\
    ...         '<tr>'\\
    ...             '<th>trumpet</th>'\\
    ...             '<td>0</td>'\\
    ...             '<td>0</td>'\\
    ...             '<td>1</td>'\\
    ...             '<td>1</td>'\\
    ...             '<td>0</td>'\\
    ...             '<td>2</td>'\\
    ...         '</tr>'\\
    ...     '</tbody>'\\
    ...     '<tfoot>'\\
    ...         '<tr>'\\
    ...             '<th>OVERALL</th>'\\
    ...             '<td>2</td>'\\
    ...             '<td>1</td>'\\
    ...             '<td>1</td>'\\
    ...             '<td>1</td>'\\
    ...             '<td>1</td>'\\
    ...             '<td>6</td>'\\
    ...         '</tr>'\\
    ...     '</tfoot>'\\
    ... '</table>'

..
    >>> awaited == re.sub(' |\\n|<BLANKLINE>', '', str(response))
    True

"""

from django.db import models

class Instrument(models.Model):
    name = models.CharField(max_length=100)
    def __unicode__(self):
        return u'%s' % self.name

class Musician(models.Model):
    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    instrument = models.ForeignKey(Instrument)
    def __unicode__(self):
        return u'%s %s' % (self.firstname, self.lastname)
    
class Song(models.Model):
    title = models.CharField(max_length=100)
    release_date = models.DateField()
    author = models.ForeignKey(Musician)
    def __unicode__(self):
        return u'%s' % self.title

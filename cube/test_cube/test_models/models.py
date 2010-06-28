"""
.. 
    >>> from cube.base import Cube
    >>> import copy

Cube
======

..
    >>> from datetime import datetime, date

A super simple aggregation function

    >>> def count_qs(queryset):
    ...     return queryset.count()

Some data

    >>> trumpet = Instrument(name='trumpet')
    >>> piano = Instrument(name='piano')
    >>> sax = Instrument(name='sax')
    >>> trumpet.save() ; piano.save() ; sax.save()

    >>> miles_davis = Musician(firstname='Miles', lastname='Davis', instrument=trumpet)
    >>> freddie_hubbard = Musician(firstname='Freddie', lastname='Hubbard', instrument=trumpet)
    >>> erroll_garner = Musician(firstname='Erroll', lastname='Garner', instrument=piano)
    >>> bill_evans_p = Musician(firstname='Bill', lastname='Evans', instrument=piano)
    >>> thelonious_monk = Musician(firstname='Thelonious', lastname='Monk', instrument=piano)
    >>> bill_evans_s = Musician(firstname='Bill', lastname='Evans', instrument=sax)
    >>> miles_davis.save() ; freddie_hubbard.save() ; erroll_garner.save() ; bill_evans_p.save() ; thelonious_monk.save() ; bill_evans_s.save()

    >>> so_what = Song(title='So What', author=miles_davis, release_date=date(1959, 8, 17))
    >>> all_blues = Song(title='All Blues', author=miles_davis, release_date=date(1959, 8, 17))
    >>> blue_in_green = Song(title='Blue In Green', author=bill_evans_p, release_date=date(1959, 8, 17))
    >>> south_street_stroll = Song(title='South Street Stroll', author=freddie_hubbard, release_date=date(1969, 1, 21))
    >>> well_you_neednt = Song(title='Well You Needn\\'t', author=thelonious_monk, release_date=date(1944, 2, 1))
    >>> blue_monk = Song(title='Blue Monk', author=thelonious_monk, release_date=date(1945, 2, 1))
    >>> so_what.save() ; all_blues.save() ; blue_in_green.save() ; south_street_stroll.save() ; well_you_neednt.save() ; blue_monk.save()

Let's create a cube

    >>> c = Cube(['instrument__name', 'firstname'], Musician.objects.all(), count_qs)

Getting sample space of a dimension
--------------------------------------

    >>> c1 = Cube(['author', 'release_date'], Song.objects.all(), count_qs)

    >>> c1.get_sample_space('title') == sorted(set(['So What', 'All Blues', 'Blue In Green', 'South Street Stroll', 'Well You Needn\\'t', 'Blue Monk']))
    True
    >>> c1.get_sample_space('release_date__year') == sorted(set([1944, 1969, 1959, 1945]))
    True
    >>> c1.get_sample_space('release_date__absmonth') == sorted(set([datetime(1969, 1, 1, 0, 0), datetime(1945, 2, 1, 0, 0), datetime(1944, 2, 1, 0, 0), datetime(1959, 8, 1, 0, 0)]))
    True
    >>> c1.get_sample_space('release_date__absday') == sorted(set([datetime(1969, 1, 21, 0, 0), datetime(1945, 2, 1, 0, 0), datetime(1944, 2, 1, 0, 0), datetime(1959, 8, 17, 0, 0)]))
    True
    >>> c1.get_sample_space('author__instrument__name') == sorted(['piano', 'trumpet'])
    True
    >>> set(c1.get_sample_space('author__instrument')) == set([piano, trumpet])
    True
    >>> c1.get_sample_space('author__firstname') == sorted(['Bill', 'Miles', 'Thelonious', 'Freddie'])
    True
    >>> set(c1.get_sample_space('author')) == set([miles_davis, freddie_hubbard, erroll_garner, bill_evans_p, thelonious_monk, bill_evans_s])
    True

..
    
    ----- Formatting datetimes constraint

    >>> c1._format_constraint({'attribute__date__absmonth': date(3000, 7, 1)}) == {'attribute__date__month': 7, 'attribute__date__year': 3000}
    True
    >>> c1._format_constraint({'attribute__date__absday': datetime(1990, 8, 23, 0, 0, 0)}) == {'attribute__date__day': 23, 'attribute__date__month': 8, 'attribute__date__year': 1990}
    True

    ----- Shallow copy
    
    >>> c1_copy = copy.copy(c1)
    >>> id(c1_copy) != id(c1)
    True
    >>> id(c1_copy.dimensions) != id(c1.dimensions) ; c1_copy.dimensions == c1.dimensions
    True
    True
    >>> id(c1_copy.sample_space) != id(c1.sample_space) ; c1_copy.sample_space == c1.sample_space
    True
    True
    >>> id(c1_copy.constraint) != id(c1.constraint) ; c1_copy.constraint == c1.constraint
    True
    True
    >>> id(c1_copy.queryset) != id(c1.queryset) ; list(c1_copy.queryset) == list(c1.queryset)
    True
    True
    >>> c1_copy.aggregation == c1.aggregation
    True

Explicitely give the cube's sample space
-----------------------------------------

    >>> c = Cube(['instrument__name', 'firstname'], Musician.objects.all(), count_qs, sample_space={'instrument__name': ['trumpet', 'piano']})
    >>> c.get_sample_space('instrument__name') == sorted(['trumpet', 'piano'])
    True

Resample the sample space of a cube's dimension
-------------------------------------------------

    >>> c = Cube(['release_date__absmonth', 'author__lastname'], Song.objects.all(), count_qs)
    >>> set(c.get_sample_space('release_date__absmonth')) == set([datetime(1969, 1, 1, 0, 0), datetime(1945, 2, 1, 0, 0), datetime(1944, 2, 1, 0, 0), datetime(1959, 8, 1, 0, 0)])
    True
    >>> c = c.resample('release_date__absmonth', lbound=datetime(1945, 1, 1), ubound=datetime(1960, 11, 1))
    >>> set(c.get_sample_space('release_date__absmonth')) == set([datetime(1959, 8, 1, 0, 0), datetime(1945, 2, 1, 0, 0)])
    True

Getting a measure from the cube
--------------------------------

    >>> c = Cube(['firstname', 'instrument__name'], Musician.objects.all(), count_qs)
    >>> c.measure(firstname='Miles')
    1
    >>> c.measure(firstname='Bill')
    2
    >>> c.measure(firstname='Miles', instrument__name='trumpet')
    1
    >>> c.measure(firstname='Miles', instrument__name='piano')
    0
    >>> c.measure()
    6

Iterate over cube's subcubes
----------------------------

    >>> c = Cube(['firstname', 'instrument__name'], Musician.objects.all(), count_qs)
    >>> list(c.subcubes('firstname'))
    [Cube(instrument__name, firstname=Bill), Cube(instrument__name, firstname=Erroll), Cube(instrument__name, firstname=Freddie), Cube(instrument__name, firstname=Miles), Cube(instrument__name, firstname=Thelonious)]

Multidimensionnal dictionnary of measures
-------------------------------------------

    >>> c = c.resample('instrument__name', space=['piano', 'trumpet']).resample('firstname', space=['Philly', 'Bill', 'Miles'])
    >>> c.measure_dict('firstname', 'instrument__name') == {
    ...     'Bill': {
    ...         'piano': {'measure': 1},
    ...         'trumpet': {'measure': 0},
    ...         'measure': 2
    ...     },
    ...     'Miles': {
    ...         'piano': {'measure': 0},
    ...         'trumpet': {'measure': 1},
    ...         'measure': 1
    ...     },
    ...     'Philly': {
    ...         'piano': {'measure': 0},
    ...         'trumpet': {'measure': 0},
    ...         'measure': 0
    ...     },
    ...     'measure': 6
    ... }
    True

    >>> c.measure_dict('firstname', 'instrument__name', full=False) == {
    ...     'Bill': {
    ...         'piano': {'measure': 1},
    ...         'trumpet': {'measure': 0},
    ...     },
    ...     'Miles': {
    ...         'piano': {'measure': 0},
    ...         'trumpet': {'measure': 1},
    ...     },
    ...     'Philly': {
    ...         'piano': {'measure': 0},
    ...         'trumpet': {'measure': 0},
    ...     },
    ... }
    True

Multidimensionnal list of measures
------------------------------------

    >>> c.measure_list('firstname', 'instrument__name') == [
    ...     [1, 0],
    ...     [0, 1],
    ...     [0, 0],
    ... ]
    True

Getting a subcube
------------------

By constraining the cube

    >>> subcube = c.constrain(instrument__name='trumpet')
    >>> subcube.measure_dict('firstname', 'instrument__name', full=False) == {
    ...     'Miles': {
    ...         'trumpet': {'measure': 1},
    ...     },
    ...     'Bill': {
    ...         'trumpet': {'measure': 0},
    ...     },
    ...     'Philly': {
    ...         'trumpet': {'measure': 0},
    ...     },
    ... }
    True


It is also possible to use Django field-lookup syntax for date dimensions :

    >>> c1 = Cube(['author__lastname', 'release_date__month', 'release_date__year'], Song.objects.all(), len)
    >>> subcube = c1.constrain(release_date__month=2)
    >>> subcube.measure_dict('release_date__month', 'release_date__year', 'author__lastname', full=False) == {
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

Ordering the results
----------------------

    >>> 

Use django field lookup syntax in dimensions
-----------------------------------------------

    >>> c1 = Cube(['instrument__name__in', 'firstname'], Musician.objects.all(), len, sample_space={
    ...     'instrument__name__in': [('trumpet', 'piano'), ('trumpet', 'sax'), ('sax', 'piano')],
    ...     'firstname': ['Miles', 'Erroll', 'Bill']
    ... })
    >>> c1.measure_dict('instrument__name__in', 'firstname', full=False) == {
    ...     ('trumpet', 'piano'): {
    ...         'Bill': {'measure': 1},
    ...         'Erroll': {'measure': 1},
    ...         'Miles': {'measure': 1},
    ...     },
    ...     ('trumpet', 'sax'): {
    ...         'Bill': {'measure': 1},
    ...         'Erroll': {'measure': 0},
    ...         'Miles': {'measure': 1},
    ...     },
    ...     ('sax', 'piano'): {
    ...         'Bill': {'measure': 2},
    ...         'Erroll': {'measure': 1},
    ...         'Miles': {'measure': 0},
    ...     },
    ... }
    True


Creating a cube from other cubes + - * /
------------------------------------------

    >>> 


Template tags
==============
..

    >>> from cube.templatetags import cube_templatetags
    >>> from django.template import Template, Context, Variable
    >>> import re

Iterating over cube's subcubes
-------------------------------

    >>> c = Cube(['firstname', 'lastname', 'instrument__name'], Musician.objects.all(), len, sample_space={
    ...     'firstname': ['Miles'],
    ...     'instrument__name': ['trumpet', 'piano'],
    ...     'lastname': ['Davis', 'Evans']
    ... })

    >>> context = Context({'my_cube': c})

    >>> template = Template(
    ...     '{% load cube_templatetags %}'
    ...     '{% subcubes my_cube by firstname, instrument__name as subcube1 %}'
    ...     '   {{ subcube1 }}:{{ subcube1.measure }}'
    ...     '   {% subcubes subcube1 by lastname as subcube2 %}'
    ...     '      {{ subcube2 }}:{{ subcube2.measure }}'
    ...     '   {% endsubcubes %}'
    ...     '{% endsubcubes %}'
    ... )

    >>> awaited = re.sub(' ', '', ''
    ... '   Cube(lastname, firstname=Miles, instrument__name=piano):0'
    ... '      Cube(firstname=Miles, instrument__name=piano, lastname=Davis):0'
    ... '      Cube(firstname=Miles, instrument__name=piano, lastname=Evans):0'
    ... '   Cube(lastname, firstname=Miles, instrument__name=trumpet):1'
    ... '      Cube(firstname=Miles, instrument__name=trumpet, lastname=Davis):1'
    ... '      Cube(firstname=Miles, instrument__name=trumpet, lastname=Evans):0'
    ... )

    >>> awaited == re.sub(' ', '', template.render(context))
    True

Get a constraint value
------------------------

    >>> c = Cube(['firstname', 'lastname', 'instrument__name'], Musician.objects.all(), count_qs, constraint={
    ...     'firstname': 'John',
    ...     'instrument__name': 'sax',
    ... })
    >>> context = Context({'my_cube': c})

    >>> template = Template(
    ... '{% load cube_templatetags %}'
    ... '>FUNKY<{{ my_cube|getconstraint:\\'instrument__name\\' }}>FUNKY<'
    ... )
    >>> template.render(context)
    u'>FUNKY<sax>FUNKY<'
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

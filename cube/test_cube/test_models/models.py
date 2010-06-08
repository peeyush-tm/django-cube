"""
.. 
    >>> from cube.base import Coords, Cube

Coords
=======

Creation
----------
    >>> coord1 = Coords(x=0, y='bottom')
    >>> coord1.x
    0
    >>> coord1.y
    'bottom'

__repr__
----------
    >>> coord1
    Coords(x=0, y='bottom')

__hash__
----------
    >>> coord1 = Coords(x='top', altitude='a lot', y=23)
    >>> coord2 = Coords(y=23, x='top', altitude='a lot')
    >>> hash(coord1) == hash(coord2)
    True

    >>> coord1 = Coords(x='top', altitude='a lot', y=23)
    >>> coord2 = Coords(y=23, x='top', altitude='lot')
    >>> hash(coord1) == hash(coord2)
    False

'dictionnary-ness'
-----------------------
    >>> items = [(key, value) for key, value in coord1.iteritems()]
    >>> ('x', 'top') in items
    True
    >>> ('altitude', 'a lot') in items
    True
    >>> ('y', 23) in items
    True

    >>> dict(coord1) == {'x': 'top', 'altitude': 'a lot', 'y': 23}
    True
    
    >>> Coords(x=1, y=2) == Coords(y=2, x=1)
    True

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

.. 
    Getting sample space of a dimension
    --------------------------------------
    >>> c1 = Cube(['author', 'release_date'], Song.objects.all(), count_qs)

    >>> c1._get_sample_space('title') == set(['So What', 'All Blues', 'Blue In Green', 'South Street Stroll', 'Well You Needn\\'t', 'Blue Monk'])
    True
    >>> c1._get_sample_space('release_date__year') == set([datetime(1944, 1, 1, 0, 0), datetime(1969, 1, 1, 0, 0), datetime(1959, 1, 1, 0, 0), datetime(1945, 1, 1, 0, 0)])
    True
    >>> c1._get_sample_space('release_date__month') == set([datetime(1944, 2, 1, 0, 0), datetime(1945, 2, 1, 0, 0), datetime(1969, 1, 1, 0, 0), datetime(1959, 8, 1, 0, 0)])
    True
    >>> c1._get_sample_space('author__instrument__name') == set(['piano', 'trumpet', 'sax'])
    True
    >>> c1._get_sample_space('author__instrument') == set([piano, trumpet, sax])
    True
    >>> c1._get_sample_space('author__firstname') == set(['Bill', 'Miles', 'Thelonious', 'Freddie', 'Erroll'])
    True
    >>> c1._get_sample_space('author') == set([miles_davis, freddie_hubbard, erroll_garner, bill_evans_p, thelonious_monk, bill_evans_s])
    True
        
    Formatting datetimes constraints
    ----------------------------------
    >>> c1._format_constraint({'attribute__date__year': date(1984, 1, 1)}) == {'attribute__date__year': 1984}
    True
    >>> c1._format_constraint({'attribute__date__month': date(3000, 7, 1)}) == {'attribute__date__month': 7}
    True
    >>> c1._format_constraint({'attribute__date__day': datetime(1990, 8, 23, 0, 0, 0)}) == {'attribute__date__day': 23}
    True

Iterating on the cube's results
----------------------------------

    >>> meas_list = [(coords, measure) for coords, measure in c.iteritems()]
    >>> len(meas_list) == 5 * 3
    True
    >>> meas_dict = dict(c.iteritems())
    >>> meas_dict[Coords(instrument__name='trumpet', firstname='Bill')]
    0
    >>> meas_dict[Coords(firstname='Miles', instrument__name='trumpet')]
    1
    >>> meas_dict == {Coords(instrument__name=u'trumpet', firstname='Miles'): 1,
    ...             Coords(instrument__name=u'trumpet', firstname='Freddie'): 1,
    ...             Coords(instrument__name=u'trumpet', firstname='Erroll'): 0,
    ...             Coords(instrument__name=u'trumpet', firstname='Bill'): 0,
    ...             Coords(instrument__name=u'trumpet', firstname='Thelonious'): 0,
    ...             Coords(instrument__name=u'piano', firstname='Miles'): 0,
    ...             Coords(instrument__name=u'piano', firstname='Freddie'): 0,
    ...             Coords(instrument__name=u'piano', firstname='Erroll'): 1,
    ...             Coords(instrument__name=u'piano', firstname='Bill'): 1,
    ...             Coords(instrument__name=u'piano', firstname='Thelonious'): 1,
    ...             Coords(instrument__name=u'sax', firstname='Miles'): 0,
    ...             Coords(instrument__name=u'sax', firstname='Freddie'): 0,
    ...             Coords(instrument__name=u'sax', firstname='Erroll'): 0,
    ...             Coords(instrument__name=u'sax', firstname='Bill'): 1,
    ...             Coords(instrument__name=u'sax', firstname='Thelonious'): 0,
    ...             }
    True

Cube's dictionnary-ness
-------------------------

    >>> c[Coords(instrument__name=u'trumpet', firstname='Miles')]
    1
    >>> c[Coords(instrument__name=u'piano', firstname='Thelonious')]
    1
    >>> set([coord for coord in c]) == set([Coords(instrument__name=u'trumpet', firstname='Miles'),
    ...             Coords(instrument__name=u'trumpet', firstname='Freddie'),
    ...             Coords(instrument__name=u'trumpet', firstname='Erroll'),
    ...             Coords(instrument__name=u'trumpet', firstname='Bill'),
    ...             Coords(instrument__name=u'trumpet', firstname='Thelonious'),
    ...             Coords(instrument__name=u'piano', firstname='Miles'),
    ...             Coords(instrument__name=u'piano', firstname='Freddie'),
    ...             Coords(instrument__name=u'piano', firstname='Erroll'),
    ...             Coords(instrument__name=u'piano', firstname='Bill'),
    ...             Coords(instrument__name=u'piano', firstname='Thelonious'),
    ...             Coords(instrument__name=u'sax', firstname='Miles'),
    ...             Coords(instrument__name=u'sax', firstname='Freddie'),
    ...             Coords(instrument__name=u'sax', firstname='Erroll'),
    ...             Coords(instrument__name=u'sax', firstname='Bill'),
    ...             Coords(instrument__name=u'sax', firstname='Thelonious')])
    True

Getting a subcube
------------------

By reducing the cube's dimensions

    >>> subcube = c.subcube(dim=['firstname'])
    >>> meas_dict = dict(subcube)
    >>> meas_dict == {Coords(firstname='Miles'): 1,
    ...             Coords(firstname='Bill'): 2,
    ...             Coords(firstname='Thelonious'): 1,
    ...             Coords(firstname='Freddie'): 1,
    ...             Coords(firstname='Erroll'): 1}
    True
    
Or by constraining the cube

    >>> subcube = c.subcube(const={'instrument__name': 'trumpet'})
    >>> meas_dict = dict(subcube)
    >>> meas_dict == {Coords(firstname='Miles'): 1,
    ...             Coords(firstname='Freddie'): 1,
    ...             Coords(firstname='Thelonious'): 0,
    ...             Coords(firstname='Bill'): 0,
    ...             Coords(firstname='Erroll'): 0}
    True

Note that the two subcubes are very different. The first one constrains the dimension *'instrument__name'* to the value *'trumpet'*, so the measure calculated is the count of trumpet players for each firstname (which stays as a free dimension) ; whereas the second one removes the dimension *'instrument__name'*, so the measure calculated is the count of each *'firstname'*.

It is also possible to use Django field-lookup syntax for date dimensions :

    >>> c1 = Cube(['author__lastname', 'release_date__month', 'release_date__year'], Song.objects.all(), len)
    >>> subcube = c1.subcube(const={'release_date__month': 2})
    >>> meas_dict = dict(subcube)
    >>> meas_dict == {Coords(release_date__year=1945, author__lastname="Davis"): 0,
    ...             Coords(release_date__year=1945, author__lastname="Hubbard"): 0,
    ...             Coords(release_date__year=1945, author__lastname="Garner"): 0,
    ...             Coords(release_date__year=1945, author__lastname="Evans"): 0,
    ...             Coords(release_date__year=1945, author__lastname="Monk"): 1,
    ...             Coords(release_date__year=1944, author__lastname="Davis"): 0,
    ...             Coords(release_date__year=1944, author__lastname="Hubbard"): 0,
    ...             Coords(release_date__year=1944, author__lastname="Garner"): 0,
    ...             Coords(release_date__year=1944, author__lastname="Evans"): 0,
    ...             Coords(release_date__year=1944, author__lastname="Monk"): 1,
    ...             Coords(release_date__year=1969, author__lastname="Davis"): 0,
    ...             Coords(release_date__year=1969, author__lastname="Hubbard"): 0,
    ...             Coords(release_date__year=1969, author__lastname="Garner"): 0,
    ...             Coords(release_date__year=1969, author__lastname="Evans"): 0,
    ...             Coords(release_date__year=1969, author__lastname="Monk"): 0,
    ...             Coords(release_date__year=1959, author__lastname="Davis"): 0,
    ...             Coords(release_date__year=1959, author__lastname="Hubbard"): 0,
    ...             Coords(release_date__year=1959, author__lastname="Garner"): 0,
    ...             Coords(release_date__year=1959, author__lastname="Evans"): 0,
    ...             Coords(release_date__year=1959, author__lastname="Monk"): 0}
    True

Ordering the results
----------------------

    >>> subcube = c.subcube(const={'instrument__name': 'trumpet'})
    >>> meas_list = list(subcube.iteritems())
    >>> meas_list == [(Coords(firstname='Bill'), 0),
    ...             (Coords(firstname='Erroll'), 0),
    ...             (Coords(firstname='Freddie'), 1),
    ...             (Coords(firstname='Miles'), 1),
    ...             (Coords(firstname='Thelonious'), 0)]
    True

"""
from django.db import models

class Instrument(models.Model):
    name = models.CharField(max_length=100)

class Musician(models.Model):
    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    instrument = models.ForeignKey(Instrument)
    
class Song(models.Model):
    title = models.CharField(max_length=100)
    release_date = models.DateField()
    author = models.ForeignKey(Musician)    

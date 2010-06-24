# -*- coding: utf-8 -*-
#'django-cube'
#Copyright (C) 2010 Sébastien Piquemal @ futurice
#contact : sebastien.piquemal@futurice.com
#futurice's website : www.futurice.com

#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
"""
from collections import MutableMapping
import re
import copy
from datetime import date, datetime

from django.core.exceptions import FieldError
from django.db.models import ForeignKey
from django.db.models.sql import constants

from collections import defaultdict


class BaseCube(MutableMapping):
    """
    A cube that can calculate lists of measures for a queryset, on several dimensions.
    """
    def __init__(self, dimensions, aggregation, constraint={}, sample_space={}):
        """
        :param dimensions: a list of attribute names which represent the free dimensions of the cube. All Django nested field lookups are allowed. For example on a model `Person`, a possible dimension would be `mother__birth_date__in`, where `mother` would (why not?!) be foreign key to another person. You can also use two special lookups: *absmonth* and *absday* which both take :class:`datetime` or :class:`date`, and represent absolute months or days. E.g. To search for November 1986, you would have to use *'date__month=11, date__year=1986'*, instead you can just use *'date__absmonth=date(1986, 11, 1)'*.
        :param queryset: the base queryset from which the cube's sample space will be extracted.
        :param aggregation: an aggregation function. must have the following signature `def agg_func(queryset)`, and return a measure on the queryset.
        :param constraint: {*dimension*: *value*} -- a constraint that reduces the sample space of the cube.
        :param sample_space: {*dimension*: *sample_space*} -- specifies the sample space of *dimension*. If it is not specified, then default sample space is all the values that the dimension takes on the queryset.  
        """
        self.sample_space = sample_space
        self.constraint = constraint
        self.dimensions = set(dimensions)
        self.aggregation = aggregation

    def subcube(self, dimensions=None, extra_constraint={}):
        """
        :returns: Cube -- a subcube of the calling cube, whose dimensions are *dimensions*, and which is constrained with *extra_constraint*. 

        :param dimensions: list -- a subset of the calling cube's dimensions. If *dimensions* is not provided, it defaults to the calling cube's.
        :param extra_constraint: dict -- a dictionnary of constraint *{dimension: value}*. Constrained dimensions must belong to the subcube's dimensions.
        
        :raise: ValueError -- if a dimension passed along *dimensions* is not a dimension of the calling cube, or if a dimension constrained in *extra_constraint* is not a dimension of the returned subcube.
        """
        #default value for *constraint*
        constraint = copy.copy(self.constraint)
        #default value for *dimensions*
        if dimensions == None:
            dimensions = self.dimensions
        #building the new cube's *constraint*
        else:
            constraint = copy.copy(self.constraint)
            #if some dimensions are deleted, we delete also the constraints
            for dimension in (set(self.dimensions) - set(dimensions)):
                try:
                    constraint.pop(dimension)
                except KeyError:
                    pass
            constraint.update(extra_constraint)

        if not set(extra_constraint.keys()) <= set(dimensions):
            raise ValueError('%s is(are) not valid constraint dimension(s) for this cube' % (set(constraint.keys()) - set(dimensions)))
        elif not set(dimensions) <= self.dimensions:
            raise ValueError('%s is(are) not dimension(s) of the cube' % (set(dimensions) - set(self.dimensions)))
        else:
            cube_copy = copy.copy(self)
            cube_copy.dimensions = set(dimensions)
            cube_copy.constraint = constraint
            return cube_copy
     
    def subcubes(self, *dimensions):
        """
        Return an ordered list of all the sucubes of the calling cube, with *dimensions* constrained to all the possible values in their sample spaces. For example :

            >>> sample_space = {
            ...     'name': ['John', 'Jack'],
            ...     'instrument': ['Trumpet'],
            ...     'age': [14, 89],
            ... }
            >>> Cube(['name', 'instrument', 'age'], len, sample_space=sample_space).subcubes()
            [Cube(age, name='John', instrument='Trumpet'), Cube(age, name='Jack', instrument='Trumpet')]

        If one of the *dimensions* passed as parameter is already constrained in the calling cube, it is not considered as an error. The sample space taken for this dimension will merely be a singleton : the constraint value. 
        """
        dimensions = list(copy.copy(dimensions))

        for index, dimension in enumerate(dimensions):
            if dimension not in self.dimensions:
                raise ValueError("invalid dimension %s" % dimension)
            #if dimension is constrained we don't need to iterate for it.
            if dimension in self.constraint.keys():
                dimensions.pop(index)

        if len(dimensions):
            #we fix a dimension,
            fixed_dimension = dimensions.pop()
            #and create a subcube with the remaining free dimensions,
            #one for each value in the fixed dimension's sample space.
            #Every one of these cubes is constrained *fixed_dimension=value*
            sample_space = self.get_sample_space(fixed_dimension)
            for value in sample_space:
                #subcube_constraint = cube_constraint + extra_constraint
                extra_constraint = {fixed_dimension: value}
                #constrained subcube
                subcube = self.constrain(extra_constraint)
                subcube_constraint = copy.copy(subcube.constraint)
                #we yield all the measures for the constrained cube
                for subsubcube in subcube.subcubes(*dimensions):
                    yield subsubcube
            raise StopIteration

        #There is no free dimension, so we can yield the measure.
        else:
            yield self
            raise StopIteration

    def constrain(self, extra_constraint):
        """
        Merges the calling cube's constraint with *extra_constraint*.

        :returns: Cube -- a subcube of the calling cube. 
        """
        constraint = copy.copy(self.constraint)
        constraint.update(extra_constraint)
        cube_copy = copy.copy(self)
        cube_copy.constraint = constraint
        return cube_copy

    def resample(self, dimension, lbound=None, ubound=None, space=None):
        """
        Returns a copy of the calling cube, whose sample space of *dimension* is limited to : ::

            *space* INTER [*lbound*, *ubound*]

        If *space* is not defined, the sample space of the calling cube's *dimension* is taken instead.
        """
        #calculate dimension's new sample space
        new_space = space or self.get_sample_space(dimension)
        lbound = lbound or min(new_space)
        ubound = ubound or max(new_space)
        new_space = filter(lambda elem: elem >= lbound and elem <= ubound, new_space)
        #calculate cube's new sample space
        cube_space = copy.copy(self.sample_space)
        cube_space.update({dimension: new_space})        

        cube_copy = copy.copy(self)
        cube_copy.sample_space = cube_space
        return cube_copy

    def measure(self):
        """
        Calculates and returns the measure on the cube.
        """
        raise NotImplementedError

    def measure_dict(self, *free_dimensions):
        """
        Returns a multidimensionnal dictionnary of measures from the cube, structured following *free_dimensions*. For example : ::

            >>> cube(['dim1', 'dim2']).measures_dict('dim2', 'dim1') == {
            ...     dim2_val1: {
            ...         dim1_val1: {'measure': measure1_1},
            ...         dim1_val2: {'measure': measure1_2},
            ...
            ...         dim1_valN: {'measure': measure1_N},
            ...         'measure': measure1
            ...     },
            ... 
            ...     dim2_valN: {
            ...         dim1_val1: {'measure': measureN_1},
            ...         dim1_val2: {'measure': measureN_2},
            ...
            ...         dim1_valN: {'measure': measureN_N},
            ...         'measure': measureN
            ...     },
            ...     'measure': measure
            ... }

        .. todo:: if 'measure' is already in the dict ?
        """
        returned_dict = {}
        #if free dimensions, we have to fix one, and iterate over the subcubes. 
        if free_dimensions:
            free_dimensions = list(free_dimensions)
            fixed_dimension = free_dimensions.pop(0)
            for subcube in self.subcubes(fixed_dimension):
                dim_value = subcube.constraint[fixed_dimension]
                returned_dict[dim_value] = subcube.measure_dict(*free_dimensions)
        returned_dict['measure'] = self.measure()
        return returned_dict

    def measure_list(self, *free_dimensions):
        """
        Returns a multidimensionnal list of measures from the cube, structured following *free_dimensions*. For example : ::

            >>> cube(['dim1', 'dim2']).measures_list('dim2', 'dim1') == [
            ...     [measure_11_21, measure_11_22, , measure_11_2N],]
            ...     [measure_12_21, measure_12_22, , measure_12_2N],]
            ... 
            ...     [measure_1N_21, measure_1N_22, , measure_1N_2N],]
            ... ] # Where <measure_AB_CD> means measure of cube with dimA=B and dimC=D
        """
        returned_list = []
        if free_dimensions:
            free_dimensions = list(free_dimensions)
            fixed_dimension = free_dimensions.pop(0)
        else:
            return [self.measure()]
         
        if free_dimensions:
            for subcube in self.subcubes(fixed_dimension):
                returned_list.append(subcube.measure_list(*free_dimensions))
        else:
            for subcube in self.subcubes(fixed_dimension):
                returned_list.append(subcube.measure())
        return returned_list
        

    def _sort_sample_space(self, sspace):
        """
        :param sspace: the sample space to sort, can be any iterable
        :returns: list -- the sample space sorted
        """
        return sorted(list(sspace))

    def get_sample_space(self, dimension):
        """
        :returns: set -- The sample space of *dimension* for the calling cube. 
        """
        try:
            sample_space = self.sample_space[dimension]
        except KeyError:
            sample_space = self._default_sample_space(dimension)

        return self._sort_sample_space(sample_space)

    def __copy__(self):
        """
        Returns a shallow copy of the cube.
        """
        dimensions = copy.copy(self.dimensions)
        sample_space = copy.copy(self.sample_space)
        constraint = copy.copy(self.constraint)
        aggregation = self.aggregation
        return Cube(dimensions, aggregation, constraint=constraint, sample_space=sample_space)

    def __repr__(self):
        constr_dimensions = sorted(["%s=%s" % (dim, value) for dim, value in self.constraint.iteritems()])
        free_dimensions = sorted(list(self.dimensions - set(self.constraint.keys())))

        return 'Cube(%s)' % ", ".join(free_dimensions + constr_dimensions)
    
    def __getitem__(self, coordinates):
        """
        Returns the measure at *coordinates*. Every coordinate to a subcube is valid. e.g. : ::
        
            cube[Coords(dim1=val1, dim2=val2)] # is valid
            cube[Coords(dim1=val1)] #is valid to, it just doesn't
            ... # take the dimension dim2 into account when calculating the measure.
        """
        subcube = self
        for dimension, value in coordinates.iteritems():
            subcube = subcube.constrain({dimension: value})
        if set(subcube.constraint.keys()) <= set(subcube.dimensions):
            return subcube.measure()
        else:
            raise KeyError('%s' % coordinates)

    def __len__(self):
        """
        Returns the length of the sample space
        """
        length = 1
        for dimension in self.dimensions:
            length *= len(self.get_sample_space(dimension))
        return length
    
    def __iter__(self):
        """
        Iterates on the coordinates of all subcubes of dimension 0. 
        """
        #To cover the whole cube's sample space, we will :
        #1- pick one of the cube's dimensions
        #2- constrain it with every possible value, and calculate a subcube for each constraint
        #3- merge the coordinates of subcubes' measures with the constraint value

        free_dimensions = self.dimensions - set(self.constraint.keys())

        #If there are free dimensions, we need to calculate subcubes and merge the results.
        if len(free_dimensions):
            #we fix a dimension,
            fixed_dimension = free_dimensions.pop()
            #and create a subcube with the remaining free dimensions,
            #one for each value in the fixed dimension's sample space.
            #Every one of these cubes is constrained *fixed_dimension=value*
            sample_space = self.get_sample_space(fixed_dimension)
            sorted_sample_space = self._sort_sample_space(sample_space)
            for value in sorted_sample_space:
                #subcube_constraint = cube_constraint + extra_constraint
                extra_constraint = {fixed_dimension: value}
                #constrained subcube
                subcube = self.constrain(extra_constraint)
                subcube_constraint = copy.copy(subcube.constraint)
                #we yield all the measures for the constrained cube
                for coords in subcube:
                    merged_constraint = copy.copy(subcube_constraint)
                    merged_constraint.update(coords)
                    merged_coords = Coords(**merged_constraint)
                    yield merged_coords
            raise StopIteration

        #There is no free dimension, so we can yield the measure.
        else:
            yield Coords()
            raise StopIteration

    def __contains__(self, coordinates):
        """
        Returns True if *coordinates* points to a valid subcube.
        """
        try:
            self[coordinates]
        except KeyError:
            return False
        else:
            return True
    
    def __delitem__(self, key):
        raise NotImplementedError
    
    def __setitem__(self, key, value):
        raise NotImplementedError


class Cube(BaseCube):
    """
    A cube that can calculate lists of measures for a queryset, on several dimensions.
    """
    def __init__(self, dimensions, queryset, aggregation, constraint={}, sample_space={}):
        """
        :param dimensions: a list of attribute names which represent the free dimensions of the cube. All Django nested field lookups are allowed. For example on a model `Person`, a possible dimension would be `mother__birth_date__in`, where `mother` would (why not?!) be foreign key to another person. You can also use two special lookups: *absmonth* and *absday* which both take :class:`datetime` or :class:`date`, and represent absolute months or days. E.g. To search for November 1986, you would have to use *'date__month=11, date__year=1986'*, instead you can just use *'date__absmonth=date(1986, 11, 1)'*.
        :param queryset: the base queryset from which the cube's sample space will be extracted.
        :param aggregation: an aggregation function. must have the following signature `def agg_func(queryset)`, and return a measure on the queryset.
        :param constraint: {*dimension*: *value*} -- a constraint that reduces the sample space of the cube.
        :param sample_space: {*dimension*: *sample_space*} -- specifies the sample space of *dimension*. If it is not specified, then default sample space is all the values that the dimension takes on the queryset.  
        """
        super(Cube, self).__init__(dimensions, aggregation, constraint, sample_space)
        self.queryset = queryset
    
    def filter(self, **kwargs):
        """
        Filter the cube's queryset. This method is merely a wrapper around Django's `filter` function.
        """
        cube_copy = copy.copy(self)
        cube_copy.queryset = self.queryset.filter(**kwargs)
        return cube_copy

    def measure(self):
        """
        Calculates and returns the measure on the cube.
        """
        constraint = self._format_constraint(self.constraint)
        return self.aggregation(self.queryset.filter(**constraint))

    def _default_sample_space(self, dimension):
        """
        Returns the default sample space for *dimension*, which is all the values taken by *dimension* in the cube's queryset.
        
        .. todo:: rewrite prettier
        """
        sample_space = []
        lookup_list = re.split('__', dimension)

        if len(lookup_list) == 1:
            field = self.queryset.model._meta.get_field_by_name(lookup_list[0])[0]
            #if ForeignKey, we get all distinct objects of foreign model
            if type(field) == ForeignKey:
                sample_space = field.related.parent_model.objects.distinct()
            else:
                sample_space = self.queryset.values_list(lookup_list[0], flat=True).distinct()

        else:
            queryset = self.queryset

            #we assume first item is always a field_name
            key = lookup_list.pop(0)
            
            #we loop over the rest
            next_key = lookup_list.pop(0)
    
            #For the field lookup, we just assume that a 'month', 'day' or 'year' lookup is always terminal,
            #same thing for a field that is not a foreign key.
            while (key):

                #TODO this is totally wrong ! What if there is a field called 'month', 'year', ... ? Should introspect model._meta ?
                if next_key in ['day', 'month', 'year']:
                    for date in queryset.dates(key, next_key):
                        sample_space.append(getattr(date, next_key))
                    break
                elif next_key in ['absday', 'absmonth']:
                    query_key = {'absday': 'day', 'absmonth': 'month'}[next_key]
                    for date in queryset.dates(key, query_key):
                        sample_space.append(date)
                    break 
                else:
                    field = queryset.model._meta.get_field_by_name(key)[0]
                    #if ForeignKey, we get all distinct objects of foreign model
                    if type(field) == ForeignKey:
                        sample_space = queryset.values_list(key, flat=True).distinct()
                        filter_dict = {'%s__in' % field.rel.field_name: sample_space}
                        queryset = sample_space = field.related.parent_model.objects.filter(**filter_dict)
                    #else, we just return values
                    else:
                        sample_space = queryset.values_list(key, flat=True).distinct()
                        break

                key = next_key
                try:
                    next_key = lookup_list.pop(0)
                except IndexError:
                    next_key = None

        return sample_space

    @staticmethod
    def _format_constraint(constraint):
        """
        Formats a dictionnary of constraint to make them Django-orm-compatible 
        """
        constraint_copy = copy.copy(constraint)
        for dimension, value in constraint.iteritems():
            lookup_list = re.split('__', dimension)
            if (isinstance(value, date) or isinstance(value, datetime)) and lookup_list[-1] in ['absmonth', 'absday']:
                base_lookup = ''
                for lookup_value in lookup_list[:-1]:
                    base_lookup += lookup_value + '__'

                if lookup_list[-1] == 'absmonth':
                    del constraint_copy[dimension]
                    constraint_copy[base_lookup + 'month'] = value.month
                    constraint_copy[base_lookup + 'year'] = value.year
                elif lookup_list[-1] == 'absday':
                    del constraint_copy[dimension]
                    constraint_copy[base_lookup + 'day'] = value.day
                    constraint_copy[base_lookup + 'month'] = value.month
                    constraint_copy[base_lookup + 'year'] = value.year

        return constraint_copy

    def __copy__(self):
        """
        Returns a shallow copy of the cube.
        """
        dimensions = copy.copy(self.dimensions)
        queryset = copy.copy(self.queryset)
        sample_space = copy.copy(self.sample_space)
        constraint = copy.copy(self.constraint)
        aggregation = self.aggregation
        return Cube(dimensions, queryset, aggregation, constraint=constraint, sample_space=sample_space)

class BaseDimension(object):
    pass

class Coords(MutableMapping):
    def __init__(self, **kwargs):
        self._dimensions = kwargs.keys()
        for dimension, value in kwargs.iteritems():
            setattr(self, dimension, value)

    def __hash__(self):
        self._dimensions.sort()
        hash_key = ''
        for dimension in self._dimensions:
            hash_key += dimension + '=' + unicode(getattr(self, dimension))
        return hash(hash_key)
    
    def __repr__(self):
        self._dimensions.sort()
        coord_str = ''
        for dimension in self._dimensions:
            coord_str += dimension + '=' + repr(getattr(self, dimension)) + ', '  
        return 'Coords(%s)' % coord_str[:-2]
    
    def __setitem__(self, key, value):
        if not key in self._dimensions:
            raise KeyError('%s is not a valid dimension' % key)
        else:
            setattr(self, key, value)
    
    def __getitem__(self, key):
        if not key in self._dimensions:
            raise KeyError('%s is not a valid dimension' % key)
        else:
            return getattr(self, key)

    def __len__(self):
        return len(self._dimensions)
    
    def __iter__(self):
        return iter(self._dimensions)
    
    def __contains__(self, key):
        return key in self._dimensions
    
    def __delitem__(self, key):
        raise NotImplementedError
    
        
        

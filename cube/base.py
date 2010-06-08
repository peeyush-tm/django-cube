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

class Cube(MutableMapping):
    """
    A cube that can calculate lists of measures for a queryset, on several dimensions.
    """
    def __init__(self, dimensions, queryset, aggregation, constraint={}, sample_space={}):
        """
        :param dimensions: a list of attribute names which represent the free dimensions of the cube. Nested field lookups are allowed. For example on a model `Person`, a possible dimension would be `mother__birth_date__year`, where `mother` is a foreign key to another person.
        :param queryset: the base queryset from which the cube's sample space will be extracted.
        :param aggregation: an aggregation function. must have the following signature `def agg_func(queryset)`, and return a measure on the queryset.
        :param constraint: {*dimension*: *value*} -- a constraint that reduces the sample space of the cube.
        :param sample_space: {*dimension*: *sample_space*} -- specifies the sample space of *dimension*. If it is not specified, then default sample space is all the values that the dimension takes on the queryset.  
        """
        self.sample_space = sample_space
        self.constraint = constraint
        self.dimensions = set(dimensions)
        self.aggregation = aggregation
        self.queryset = queryset
        self._results = defaultdict(defaultdict)
            
    def iteritems(self):
        """
        Iterates on the items (*coordinate*, *measure*), where *coordinate* is a :class:`Coords` object, and *measure* is the value of the aggregation at *coordinate* position. There is one item for each coordinates in the cube's sample space.
        """
        #To cover the whole cube's sample space, we will :
        #1- pick one of the cube's dimensions
        #2- constrain it with every possible value, and calculate a subcube for each constraint
        #3- merge the coordinates of subcubes' measures with the constraint value, in order to get the complete coordinates of the measure

        free_dimensions = self.dimensions - set(self._constr_to_dim(self.constraint).keys())

        #If there are free dimensions, we need to calculate subcubes and merge the results.
        if len(free_dimensions):
            #we fix a dimension,
            fixed_dimension = free_dimensions.pop()
            #and create a subcube with the remaining free dimensions,
            #one for each value in the fixed dimension's sample space.
            #Every one of these cubes is constrained *fixed_dimension=value*
            sample_space = self._get_sample_space(fixed_dimension)
            sorted_sample_space = self._sort_sample_space(sample_space)
            for value in sorted_sample_space:
                #subcube_constraint = cube_constraint + extra_constraint
                extra_constraint = {fixed_dimension: value}
                extra_constraint = self._format_constraint(extra_constraint)
                subcube_constraint = copy.copy(self.constraint)
                subcube_constraint.update(extra_constraint)
                #constrained subcube
                subcube = self.constrain(extra_constraint)
                #we yield all the measures for the constrained cube
                for coords, measure in subcube.iteritems():
                    merged_constraint = copy.copy(subcube_constraint)
                    merged_constraint.update(coords)
                    merged_constraint = self._constr_to_dim(merged_constraint)
                    merged_coords = Coords(**merged_constraint)
                    yield (merged_coords, measure)
            raise StopIteration

        #There is no free dimension, so we can yield the measure.
        else:
            yield (Coords(), self._measure())
            raise StopIteration

    def subcube(self, dimensions=None, extra_constraint={}):
        """
        :returns: Cube -- a subcube of the calling cube, whose dimensions are *dimensions*, and which is constrained with *extra_constraint*. 

        :param dimensions: list -- a subset of the calling cube's dimensions. If *dimensions* is not provided, it defaults to the calling cube's.
        :param extra_constraint: dict -- a dictionnary of constraint *{dimension: value}*. Constrained dimensions must belong to the subcube's dimensions. 

        .. todo:: better checking that the constraint are valid (taking into account the field-lookup syntax)
        """
        if dimensions == None:
            dimensions = self.dimensions
        else:
            constraint_copy = copy.copy(self.constraint)
            #if some dimensions are deleted, we delete also the constraints
            for dimension in (set(self.dimensions) - set(dimensions)):
                try:
                    constraint_copy.pop(dimension)
                except:
                    pass
            constraint_copy.update(extra_constraint)
        
        #if not set(extra_constraint.keys()) <= set(dimensions):
        #    raise ValueError('%s is(are) not dimension(s) of the cube, so it cannot be constrained' % (set(constraint.keys()) - set(dimensions)))
        #else:
        return Cube(dimensions, self.queryset, self.aggregation, constraint_copy)
     
    def constrain(self, extra_constraint):
        """
        Merges the calling cube's constraint with *extra_constraint*.

        :returns: Cube -- a subcube of the calling cube. 
        """
        constraint = copy.copy(self.constraint)
        constraint.update(extra_constraint)
        return Cube(self.dimensions, self.queryset, self.aggregation, constraint)      

    def _measure(self):
        """
        Calculates and returns the measure on the cube.
        """
        return self.aggregation(self.queryset.filter(**self.constraint))

    def _sort_sample_space(self, sspace):
        """
        :param sspace: the sample space to sort, can be any iterable
        :returns: list -- the sample space sorted
        """
        return sorted(list(sspace))

    def _get_sample_space(self, dimension):
        """
        :returns: set -- The sample space of *dimension* for the calling cube. 
        """
        try:
            return self.sample_space[dimension]
        except KeyError:
            return self._default_sample_space(dimension) 

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
                else:
                    field = queryset.model._meta.get_field_by_name(key)[0]
                    #if ForeignKey, we get all distinct objects of foreign model
                    if type(field) == ForeignKey:
                        sample_space = queryset = field.related.parent_model.objects.distinct()
                    #else, we just return values
                    else:
                        sample_space = queryset.values_list(key, flat=True).distinct()
                        break

                key = next_key
                try:
                    next_key = lookup_list.pop(0)
                except IndexError:
                    next_key = None

        return set(sample_space)

    @staticmethod
    def _format_constraint(constraint):
        """
        Formats a dictionnary of constraint to make them Django-orm-compatible 
        """
        constraint_copy = copy.copy(constraint)
        for dimension, value in constraint.iteritems():
            lookup_list = re.split('__', dimension)
            if (isinstance(value, date) or isinstance(value, datetime)) and lookup_list[-1] in ['year', 'month', 'day']:
                base_lookup = ''
                for lookup_value in lookup_list[:-1]:
                    base_lookup += lookup_value + '__'

                if lookup_list[-1] == 'year':
                    constraint_copy[dimension] = value.year
                elif lookup_list[-1] == 'month':
                    constraint_copy[dimension] = value.month
                elif lookup_list[-1] == 'day':
                    constraint_copy[dimension] = value.day

        return constraint_copy

    @staticmethod
    def _constr_to_dim(constraint):
        """
        Transforms *constraint* *{dim: value}* so that if *dim* is a django field lookup, it will be transformed to a dimension. e.g. 'name__in' will be transformed to 'name'.
        """
        constraint_copy = copy.copy(constraint)
        for dimension, value in constraint.iteritems():
            lookup_list = re.split("__", dimension)
            #All the 'dimensions' that end with 'contains', 'in', ... are field lookups, so we have to trim them,
            #to keep only the base of the field lookup. This excepts the 'date' lookups, which are also dimensions.
            if (lookup_list[-1] in constants.QUERY_TERMS) and (not lookup_list[-1] in ['year', 'month', 'day', 'week_day']):
                base_lookup = ''
                for lookup_value in lookup_list[:-1]:
                    base_lookup += lookup_value + '__'
                constraint_copy[base_lookup[:-2]] = value
                del constraint_copy[dimension]
        
        return constraint_copy

    def __repr__(self):
        dim_str = ''
        for dim in self.dimensions:
            if self.constraint.get(dim):
                dim_str += dim + '=' + str(self.constraint[dim]) + ', '
            else:
                dim_str += dim + ', '
        return 'Cube(%s)' % dim_str[:-2]
    
    def __getitem__(self, coordinates):
        """
        Returns the measure at *coordinates*
        """
        return dict(self.iteritems())[coordinates]

    def __len__(self):
        """
        Returns the length of the sample space
        """
        return len(dict(self.iteritems()))
    
    def __iter__(self):
        """
        Iterates on the whole sample space
        """
        return iter(dimension for dimension, measure in self.iteritems())
    
    def __contains__(self, coordinates):
        """
        Returns True if *coordinates* belongs to the cube.
        """
        return coordinates in dict(self.iteritems())
    
    def __delitem__(self, key):
        raise NotImplementedError
    
    def __setitem__(self, key, value):
        raise NotImplementedError


class Coords(MutableMapping):
    def __init__(self, **kwargs):
        self._dimensions = kwargs.keys()
        for dimension, value in kwargs.iteritems():
            setattr(self, dimension, value)

    def __hash__(self):
        self._dimensions.sort()
        hash_key = ''
        for dimension in self._dimensions:
            hash_key += dimension + '=' + str(getattr(self, dimension))
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
    
        
        

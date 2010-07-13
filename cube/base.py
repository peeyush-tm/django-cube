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
from django.db.models import ForeignKey, FieldDoesNotExist
from django.db.models.sql import constants

from .utils import odict


class BaseDimension(object):
    def __init__(self):
        self._name = None

    @property
    def name(self):
        return self._name

class BaseCubeMetaclass(type):
    """
    """
    def __new__(cls, name, bases, attrs):
        #dictionnary containing dimensions
        dimensions = {}
        attrs_copy = copy.copy(attrs)
        for attr_name, attr_value in attrs_copy.iteritems():
            if isinstance(attr_value, BaseDimension):
                dimensions[attr_name] = attr_value
                attr_value._name = attr_name
                del attrs[attr_name]
        attrs['dimensions'] = dimensions

        return super(BaseCubeMetaclass, cls).__new__(cls, name, bases, attrs)
        
class BaseCube(object):
    """
    The base class for a cube.
    """

    __metaclass__ = BaseCubeMetaclass

    def __init__(self, constraint={}, sample_space={}):
        """
        :param constraint: {*dimension*: *value*} -- a constraint that reduces the sample space of the cube.
        :param sample_space: {*dimension*: *sample_space*} -- specifies the sample space of *dimension*. If it is not specified, then default sample space is all the values that the dimension takes on the queryset.  
        """
        self.sample_space = sample_space
        self.constraint = constraint
     
    def subcubes(self, *dim_names):
        """
        Return an ordered list of all the sucubes of the calling cube, dimensions with names in *dim_names* constrained to all the possible values in their sample spaces. For example :

            >>> sample_space = {
            ...     'name': ['John', 'Jack'],
            ...     'instrument': ['Trumpet'],
            ...     'age': [14, 89],
            ... }
            >>> Cube(['name', 'instrument', 'age'], len, sample_space=sample_space).subcubes('name', 'instrument')
            [Cube(age, name='John', instrument='Trumpet'), Cube(age, name='Jack', instrument='Trumpet')]

        If one of the dimensions passed as parameter is already constrained in the calling cube, it is not considered as an error. The sample space taken for this dimension will merely be a singleton : the constraint value. 
        """
        dim_names = list(copy.copy(dim_names))

        for index, dim_name in enumerate(dim_names):
            if dim_name not in self.dimensions:
                raise ValueError("invalid dimension %s" % dim_name)
            #if dimension is constrained we don't need to iterate for it.
            if dim_name in self.constraint:
                dim_names.pop(index)

        if len(dim_names):
            #we fix a dimension,
            fixed_dim_name = dim_names.pop()
            #and create a subcube with the remaining free dimensions,
            #one for each value in the fixed dimension's sample space.
            #Every one of these cubes is constrained *fixed_dim_name=value*
            sample_space = self.get_sample_space(fixed_dim_name)
            for value in sample_space:
                #subcube_constraint = cube_constraint + extra_constraint
                extra_constraint = {fixed_dim_name: value}
                #constrained subcube
                subcube = self.constrain(**extra_constraint)
                subcube_constraint = copy.copy(subcube.constraint)
                #we yield all the measures for the constrained cube
                for subsubcube in subcube.subcubes(*dim_names):
                    yield subsubcube
            raise StopIteration

        #There is no free dimension, so we can yield the measure.
        else:
            yield copy.copy(self)
            raise StopIteration

    def constrain(self, **extra_constraint):
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

            <space> INTER [<lbound>, <ubound>]

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

    def measure(self, **coordinates):
        """
        Calculates and returns the measure on the cube at *coordinates*. For example :
            
            >>> cube.measure(dim1=val1, dim2=val2, dimN=valN)

        If *coordinates* is empty, the measure returned is calculated on the whole cube. 
        """
        raise NotImplementedError

    def measure_dict(self, *free_dim_names, **kwargs):
        """
        Returns an ordered dictionnary of measures from the cube, structured following *free_dim_names*. For example :

            >>> cube(['dim1', 'dim2']).measures_dict('dim2', 'dim1') == {
            ...     'subcubes': {
            ...         dim2_val1: {
            ...             'subcubes': {
            ...                 dim1_val1: {'measure': measure1_1},
            ...
            ...                 dim1_valN: {'measure': measure1_N},
            ...             },
            ...             'measure': measure1
            ...         },
            ... 
            ...         dim2_valN: {
            ...
            ...         },
            ...     },
            ...     'measure': measure
            ... }

        If *full=False*, only the measures for which all dimensions in *free_dim_names* are fixed will be returned. For example : ::

            >>> cube(['dim1', 'dim2']).measures_dict('dim2', 'dim1', full=False) == {
            ...     dim2_val1: {
            ...         dim1_val1: {'measure': measure1_1},
            ...
            ...         dim1_valN: {'measure': measure1_N},
            ...     },
            ... 
            ...     dim2_valN: {
            ...
            ...     },
            ... }
        """
        full = kwargs.setdefault('full', True)
        returned_dict = odict()
        #if free dim_names, we have to fix one, and iterate over the subcubes. 
        if free_dim_names:
            free_dim_names = list(free_dim_names)
            fixed_dimension = free_dim_names.pop(0)
            subcubes_dict = odict()
            for subcube in self.subcubes(fixed_dimension):
                dim_value = subcube.constraint[fixed_dimension]
                subcubes_dict[dim_value] = subcube.measure_dict(*free_dim_names, **kwargs)
            if full:
                returned_dict['measure'] = self.measure()
                returned_dict['subcubes'] = subcubes_dict
            else:
                returned_dict = subcubes_dict
        else:
            returned_dict['measure'] = self.measure()
        return returned_dict

    def measure_list(self, *free_dim_names):
        """
        Returns a multidimensionnal list of measures from the cube, structured following *free_dim_names*. For example : ::

            >>> cube(['dim1', 'dim2']).measures_list('dim2', 'dim1') == [
            ...     [measure_11_21, measure_11_22, , measure_11_2N],
            ...     [measure_12_21, measure_12_22, , measure_12_2N],
            ... 
            ...     [measure_1N_21, measure_1N_22, , measure_1N_2N]
            ... ] # Where <measure_AB_CD> means measure of cube with dimA=valB and dimC=valD
        """
        returned_list = []
        if free_dim_names:
            free_dim_names = list(free_dim_names)
            fixed_dimension = free_dim_names.pop(0)
        else:
            return [self.measure()]
         
        if free_dim_names:
            for subcube in self.subcubes(fixed_dimension):
                returned_list.append(subcube.measure_list(*free_dim_names))
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
        :returns: list -- The sorted sample space of *dimension* for the calling cube. 
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
        sample_space = copy.copy(self.sample_space)
        constraint = copy.copy(self.constraint)
        dimensions = copy.copy(self.dimensions)
        cube_copy = self.__class__(constraint=constraint, sample_space=sample_space)
        cube_copy.dimensions = dimensions
        return cube_copy

    def __repr__(self):
        constr_dimensions = sorted(["%s=%s" % (dim, value) for dim, value in self.constraint.iteritems()])
        free_dimensions = sorted(list(set(self.dimensions) - set(self.constraint)))

        return 'Cube(%s)' % ", ".join(free_dimensions + constr_dimensions)

class Dimension(BaseDimension):
    """
    """
    pass

class Cube(BaseCube):
    """
    A cube that calculates measures on a Django queryset.
    """
    def __init__(self, queryset, constraint={}, sample_space={}, measure_none=0):
        """
        :param queryset: the base queryset from which the cube's sample space will be extracted.
        :param constraint: {*dimension*: *value*} -- a constraint that reduces the sample space of the cube.
        :param sample_space: {*dimension*: *sample_space*} -- specifies the sample space of *dimension*. If it is not specified, then default sample space is all the values that the dimension takes on the queryset.
        :param measure_none: the value that the measure should actually return if the calculation returned *None*
        """
        super(Cube, self).__init__(constraint, sample_space)
        self.queryset = queryset
        self.measure_none = measure_none

    def measure(self, **coordinates):
        constraint = copy.copy(self.constraint)

        #we check the coordinates passed
        for dim_name, value in coordinates.iteritems():
            if not dim_name in self.dimensions:
                raise ValueError("invalid dimension %s" % dim_name)
            if dim_name in self.constraint:
                raise ValueError("dimension %s is constrained" % dim_name)

        #calculate the total constraint
        constraint.update(coordinates)
        constraint = self._format_constraint(constraint)
        return self.aggregation(self.queryset.filter(**constraint)) or self.measure_none

    def reset_queryset(self, new_queryset):
        """
        Returns a copy of the calling cube, whose queryset is *new_queryset*
        """
        cube_copy = copy.copy(self)
        cube_copy.queryset = new_queryset
        return cube_copy

    def _default_sample_space(self, dim_name):
        """
        Returns the default sample space for *dim_name*, which is all the values taken by *dim_name* in the cube's queryset.
        
        .. todo:: rewrite prettier
        """
        sample_space = []
        lookup_list = re.split('__', dim_name)

        if len(lookup_list) == 1:
            key = lookup_list[0]
            try:
                field = self.queryset.model._meta.get_field_by_name(key)[0]
            except FieldDoesNotExist:
                raise ValueError("invalid dimension '%s', because '%s' is an invalid field name for %s"\
                    % (dim_name, key, self.queryset.model))
            #if ForeignKey, we get all distinct objects of foreign model
            if type(field) == ForeignKey:
                sample_space = field.related.parent_model.objects.distinct()
            else:
                sample_space = self.queryset.values_list(key, flat=True).distinct()

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
                    try:
                        field = queryset.model._meta.get_field_by_name(key)[0]
                    except FieldDoesNotExist:
                        raise ValueError("invalid dimension %s, because %s is an invalid field name for %s"\
                            % (dim_name, key, queryset.model))
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
        for dim_name, value in constraint.iteritems():
            lookup_list = re.split('__', dim_name)
            if (isinstance(value, date) or isinstance(value, datetime)) and lookup_list[-1] in ['absmonth', 'absday']:
                base_lookup = ''
                for lookup_value in lookup_list[:-1]:
                    base_lookup += lookup_value + '__'

                if lookup_list[-1] == 'absmonth':
                    del constraint_copy[dim_name]
                    constraint_copy[base_lookup + 'month'] = value.month
                    constraint_copy[base_lookup + 'year'] = value.year
                elif lookup_list[-1] == 'absday':
                    del constraint_copy[dim_name]
                    constraint_copy[base_lookup + 'day'] = value.day
                    constraint_copy[base_lookup + 'month'] = value.month
                    constraint_copy[base_lookup + 'year'] = value.year

        return constraint_copy

    def __copy__(self):
        """
        Returns a shallow copy of the cube.
        """
        queryset = copy.copy(self.queryset)
        sample_space = copy.copy(self.sample_space)
        constraint = copy.copy(self.constraint)
        dimensions = copy.copy(self.dimensions)
        cube_copy = self.__class__(queryset, constraint=constraint, sample_space=sample_space)
        cube_copy.dimensions = dimensions
        return cube_copy

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
import re
import copy
from datetime import date, datetime

from django.core.exceptions import FieldError
from django.db.models import ForeignKey, FieldDoesNotExist, Model
from django.db.models.sql import constants

from base import BaseDimension, BaseCube

class Dimension(BaseDimension):
    """
    A dimension that is associated with a Django model's field.

    Kwargs:
        - sample_space (iterable|callable): The sample space of the dimension to create. If this parameter is a callable, the call will receive the dimension's base queryset as only parameter, and must return a list.
        - field (str): The name of the model's field this dimension refers to. 
        - queryset (Queryset): A queryset to take the default sample space from. Usefull if the parameter *sample_space* is not given. Defaults to the dimension's cube's queryset.
    """
    def __init__(self, field=None, queryset=None, sample_space=[]):
        """
        """
        super(Dimension, self).__init__(sample_space=sample_space)
        self._field = field
        self.queryset = queryset

    @property
    def field(self):
        """
        Returns:
            str. The name of the model's field this dimension refers to.
        """
        return self._field or self._name

    def get_sample_space(self):
        """
        Returns:
            list. The sorted sample space of the calling dimension. 
        """
        #if sample_space is given... 
        if self.sample_space:
            #... is it iterable ?
            try:
                sample_space = list(self.sample_space)
            except TypeError:
                #... it is callable ?
                if hasattr(self.sample_space, '__call__'):
                    sample_space = self.sample_space(self.queryset)
                else:
                    raise TypeError('\'%s\' unvalid \'sample_space\' attribute, because it is not iterable nor callable')
        else:
            sample_space = self._default_sample_space()

        return self._sort_sample_space(sample_space)

    def to_queryset_filter(self):
        """
        Returns:
            dict. The django queryset filter equivalent to this dimension and its constraint. Returns *{}* if the dimension is not constrained. 
        """
        filter_dict = {}
        lookup_list = re.split('__', self.field)

        if not self.constraint:
            pass
        elif (isinstance(self.constraint, date) or isinstance(self.constraint, datetime)) and lookup_list[-1] in ['absmonth', 'absday']:
            base_lookup = ''
            for lookup_value in lookup_list[:-1]:
                base_lookup += lookup_value + '__'

            if lookup_list[-1] == 'absmonth':
                filter_dict[base_lookup + 'month'] = self.constraint.month
                filter_dict[base_lookup + 'year'] = self.constraint.year
            elif lookup_list[-1] == 'absday':
                filter_dict[base_lookup + 'day'] = self.constraint.day
                filter_dict[base_lookup + 'month'] = self.constraint.month
                filter_dict[base_lookup + 'year'] = self.constraint.year
        else:
            filter_dict.update({self.field: self.constraint})
        return filter_dict

    def _default_sample_space(self):
        """
        .. todo:: rewrite prettier
        """
        sample_space = []
        if not self.queryset: return []
        lookup_list = re.split('__', self.field)

        if len(lookup_list) == 1:
            key = lookup_list[0]
            try:
                field = self.queryset.model._meta.get_field_by_name(key)[0]
            except FieldDoesNotExist:
                raise ValueError("invalid field '%s', because '%s' is an invalid field name for %s"\
                    % (self.field, key, self.queryset.model))
            #if ForeignKey, we get all distinct objects of foreign model
            if type(field) == ForeignKey:
                sample_space = self.queryset.values_list(key, flat=True).distinct()
                filter_dict = {'%s__in' % field.rel.field_name: sample_space}
                sample_space = field.related.parent_model.objects.filter(**filter_dict)
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
                        raise ValueError("invalid field %s, because %s is an invalid field name for %s"\
                            % (self.field, key, queryset.model))
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
    
    def _sort_sample_space(self, sample_space):
        """
        override the parent method, in order to sort the list of django models by their *pk*.
        """
        if sample_space and isinstance(sample_space[0], Model):
            return sorted(sample_space, key=lambda item: item.pk)
        else:
            return super(Dimension, self)._sort_sample_space(sample_space)

class Cube(BaseCube):
    """
    A cube that can calculates measures on Django querysets.

    Args:
        queryset (Queryset): the base queryset of the cube. All measures will be calculated from filtered querysets of this base queryset. The way these querysets are filtered, depends on the cube's constraint.
    """

    def __init__(self, queryset, measure_none=0):
        """
        Args:
            measure_none (object): the value that the measure should actually return if the calculation returned *None*
        """
        super(Cube, self).__init__()
        self.queryset = queryset
        self.measure_none = measure_none

        #give all the dimensions a default queryset if they don't already have one.
        for dim_name, dimension in self.dimensions.iteritems():
            dimension.queryset = dimension.queryset or queryset

    def measure(self, **coordinates):
        if coordinates:
            #realizes some local copies
            constraint = dict(self.constraint)
            coordinates = dict(coordinates)

            #we check the coordinates passed
            for dim_name, value in coordinates.iteritems():
                if not dim_name in self.dimensions:
                    raise ValueError("invalid dimension '%s'" % dim_name)
                #If dimension is already constrained, we only accept the same value in *coordinates*
                if dim_name in self.constraint and constraint[dim_name] != value:
                    raise ValueError("dimension '%s' is already constrained to a different value" % dim_name)

            #we get a subcube constrained with *coordinates*, and calculate the measure on this whole subcube. 
            return self.constrain(**coordinates).measure()
        else:
            #we build the filters for the queryset
            filters_dict = {}
            for dim_name, dimension in self.dimensions.iteritems():
                filters_dict.update(dimension.to_queryset_filter())
            return self.aggregation(self.queryset.filter(**filters_dict)) or self.measure_none

    @staticmethod
    def aggregation(queryset):
        """
        Abstract method. Given a *queryset*, this method should calculate and return the measure. For example :

        >>> def aggregation(queryset):
        ...     return queryset.count()
        
        **In practice**, the *queryset* received as a parameter will **always** be : the cube's base queryset, filtered according to the cube's constraints.
        """
        raise NotImplementedError

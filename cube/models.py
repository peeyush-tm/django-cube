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
from django.db.models import ForeignKey, FieldDoesNotExist
from django.db.models.sql import constants

from base import BaseDimension, BaseCube

class Dimension(BaseDimension):
    """
    """
    def __init__(self, field=None, queryset=None, sample_space=[]):
        super(Dimension, self).__init__(sample_space=sample_space)
        self._field = field
        self.queryset = queryset

    @property
    def field(self):
        return self._field or self._name

    def to_queryset_filter(self, value):
        """
        """
        filter_dict = {}
        lookup_list = re.split('__', self.field)
        if (isinstance(value, date) or isinstance(value, datetime)) and lookup_list[-1] in ['absmonth', 'absday']:
            base_lookup = ''
            for lookup_value in lookup_list[:-1]:
                base_lookup += lookup_value + '__'

            if lookup_list[-1] == 'absmonth':
                filter_dict[base_lookup + 'month'] = value.month
                filter_dict[base_lookup + 'year'] = value.year
            elif lookup_list[-1] == 'absday':
                filter_dict[base_lookup + 'day'] = value.day
                filter_dict[base_lookup + 'month'] = value.month
                filter_dict[base_lookup + 'year'] = value.year
        else:
            filter_dict.update({self.field: value})
        return filter_dict

    def get_sample_space(self):
        """
        :returns: list -- The sorted sample space of *dimension* for the calling cube. 
        """
        sample_space = self.sample_space or self._default_sample_space()
        return self._sort_sample_space(sample_space)

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
    
    def __copy__(self):
        sample_space = copy.copy(self.sample_space)
        queryset = copy.copy(self.queryset)
        dimension_copy = Dimension(sample_space=sample_space, field=self.field, queryset=queryset)
        dimension_copy._name = self._name
        return dimension_copy

class Cube(BaseCube):
    """
    A cube that calculates measures on a Django queryset.
    """
    def __init__(self, queryset, constraint={}, measure_none=0):
        """
        :param queryset: the base queryset from which the cube's sample space will be extracted.
        :param constraint: {*dimension*: *value*} -- a constraint that reduces the sample space of the cube.
        :param measure_none: the value that the measure should actually return if the calculation returned *None*
        """
        super(Cube, self).__init__(constraint)
        self.queryset = queryset
        self.measure_none = measure_none
        for dim_name, dimension in self.dimensions.iteritems():
            dim_copy = copy.copy(dimension)
            self.dimensions[dim_name] = dim_copy
            if not dim_copy.queryset:
                dim_copy.queryset = queryset

    def measure(self, **coordinates):
        constraint = copy.copy(self.constraint)

        #we check the coordinates passed
        for dim_name, value in coordinates.iteritems():
            if not dim_name in self.dimensions:
                raise ValueError("invalid dimension %s" % dim_name)
            if dim_name in self.constraint:
                raise ValueError("dimension %s is constrained" % dim_name)

        #calculate the filter to apply to queryset
        constraint.update(coordinates)
        queryset_filters = {}
        for dim_name, value in constraint.iteritems():
            dimension = self.dimensions[dim_name]
            queryset_filters.update(dimension.to_queryset_filter(value))
        return self.aggregation(self.queryset.filter(**queryset_filters)) or self.measure_none

    def reset_queryset(self, new_queryset):
        """
        Returns a copy of the calling cube, whose queryset is *new_queryset*
        """
        cube_copy = copy.copy(self)
        cube_copy.queryset = new_queryset
        return cube_copy

    def __copy__(self):
        """
        Returns a shallow copy of the cube.
        """
        queryset = copy.copy(self.queryset)
        constraint = copy.copy(self.constraint)
        cube_copy = self.__class__(queryset, constraint=constraint)
        return cube_copy

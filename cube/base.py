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
import copy

from .utils import odict


class BaseDimension(object):
    def __init__(self, sample_space=[]):
        self._name = None
        self.sample_space = sample_space

    @property
    def name(self):
        return self._name

    def _sort_sample_space(self, sspace):
        """
        :param sspace: the sample space to sort, can be any iterable
        :returns: list -- the sample space sorted
        """
        return sorted(list(sspace))

    def get_sample_space(self):
        """
        :returns: list -- The sorted sample space of *dimension* for the calling cube. 
        """
        return self._sort_sample_space(self.sample_space)

    def __copy__(self):
        sample_space = copy.copy(self.sample_space)
        dimension_copy = Dimension(sample_space=sample_space)
        dimension_copy._name = self._name
        return dimension_copy

class BaseCubeMetaclass(type):
    #Metaclass for BaseCube
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

    def __init__(self, constraint={}):
        """
        :param constraint: {*dimension*: *value*} -- a constraint that reduces the sample space of the cube.
        """
        self.constraint = constraint
        self.dimensions = copy.copy(self.dimensions)
     
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
            for value in self.get_sample_space(fixed_dim_name):
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

    def get_sample_space(self, dim_name):
        """
        """
        return self.dimensions[dim_name].get_sample_space()

    def __copy__(self):
        """
        Returns a shallow copy of the cube.
        """
        constraint = copy.copy(self.constraint)
        dimensions = copy.copy(self.dimensions)
        cube_copy = self.__class__(constraint=constraint)
        cube_copy.dimensions = dimensions
        return cube_copy

    def __repr__(self):
        constr_dimensions = sorted(["%s=%s" % (dim, value) for dim, value in self.constraint.iteritems()])
        free_dimensions = sorted(list(set(self.dimensions) - set(self.constraint)))

        return 'Cube(%s)' % ", ".join(free_dimensions + constr_dimensions)

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
    """
    The base class for a dimension of a cube.
    """

    def __init__(self, sample_space=[]):
        """
        :param sample_space: The sample space of the dimension to create.
        """
        self._name = None
        self.sample_space = sample_space
        self._constraint = None

    @property
    def name(self):
        """
        str -- The name of the dimension.
        """
        return self._name

    @property
    def constraint(self):
        """
        object -- The value to which the dimension is constrained
        """
        return self._constraint

    @constraint.setter
    def constraint(self, value):
        """
        Setter for the property :meth:`constraint`.
        """
        self._constraint = value

    def get_sample_space(self):
        """
        :returns: list -- The sorted sample space for the calling dimension. 
        """
        return self._sort_sample_space(self.sample_space)

    def _sort_sample_space(self, sspace):
        """
        :param sspace: the sample space to sort, can be any iterable
        :returns: list -- the sample space sorted
        """
        return sorted(list(sspace))

    def __copy__(self):
        sample_space = copy.copy(self.sample_space)
        dimension_copy = Dimension(sample_space=sample_space)
        dimension_copy._name = self._name
        return dimension_copy

class BaseCubeOptions(object):
    """
    'Container' object for meta informations on a cube class. 
    """
    def __init__(self):
        self.dimensions = None

class BaseCubeMetaclass(type):
    """
    Metaclass for :class:`BaseCube`.
    """
    def __new__(cls, name, bases, attrs):
        #meta informations on a cube class
        attrs['_meta'] = BaseCubeOptions()

        #We gather in *dimensions* all the dimensions found in *attrs*
        dimensions = {}
        attrs_copy = copy.copy(attrs)
        for attr_name, attr_value in attrs_copy.iteritems():
            if isinstance(attr_value, BaseDimension):
                dimensions[attr_name] = attr_value
                attr_value._name = attr_name
                #we don't want the dimension to be an attribute of *BaseCube*
                del attrs[attr_name]

        attrs['_meta'].dimensions = dimensions
        return super(BaseCubeMetaclass, cls).__new__(cls, name, bases, attrs)
        
class BaseCube(object):
    """
    The base class for a cube.
    """

    __metaclass__ = BaseCubeMetaclass

    def __new__(cls, *args, **kwargs):
        """
        Provides the instance with local copies of the dimensions declared at the class level.
        """
        new_cube = super(BaseCube, cls).__new__(cls)
        
        #overrides the dimensions from the class with local copies
        new_cube.dimensions = copy.deepcopy(cls._meta.dimensions)
        
        return new_cube
     
    def subcubes(self, *dim_names):
        """
        Return an ordered iterator, on all the sucubes with dimensions in *dim_names* constrained. For example :

            >>> class MyCube(Cube):
            ...     name = Dimension(sample_space=['John', 'Jack'])
            ...     instrument = Dimension(sample_space=['Trumpet'])
            ...     age = Dimension(sample_space=[14, 89])

            >>> list(MyCube().subcubes('name', 'instrument'))
            [Cube(age, instrument='Trumpet', name='Jack'), Cube(age, instrument='Trumpet', name='John')]

        .. note:: If one of the dimensions whose name passed as parameter is already constrained in the calling cube, it is not considered as an error.
        """
        dim_names = list(dim_names)
        free_dim_name = self._pop_first_dim(dim_names, free_only=True)

        if free_dim_name:
            #We create one subcube for each value in the free dimension's sample space.
            #Every one of these cubes is constrained *free_dim_name=value*
            for value in self.get_sample_space(free_dim_name):
                #subcube constraint = cube constraint + extra constraint
                extra_constraint = {free_dim_name: value}
                subcube = self.constrain(**extra_constraint)
                #we yield all the subcubes of the constrained subcube with the remaining dimensions
                for subsubcube in subcube.subcubes(*dim_names):
                    yield subsubcube
            raise StopIteration

        #There is no free dimension, so we can yield the measure.
        else:
            yield copy.copy(self)
            raise StopIteration

    def constrain(self, **extra_constraint):
        """
        Merges (or overrides) the calling cube's constraint with *extra_constraint*.

        :returns: Cube -- a subcube of the calling cube, with the new constraint.
        """
        cube_copy = copy.copy(self)
        dimensions = cube_copy.dimensions

        for dim_name, value in extra_constraint.iteritems():
            try:
                dimensions[dim_name].constraint = value
            except KeyError:
                raise ValueError("invalid dimension %s" % dim_name)
        
        return cube_copy

    def measure(self, **coordinates):
        """
        Calculates and returns the measure on the cube at *coordinates*. For example :
            
            >>> cube.measure(dim1=val1, dim2=val2, dimN=valN)
            12.98

        If *coordinates* is empty, the measure returned is calculated on the whole cube. 
        """
        raise NotImplementedError

    def measure_dict(self, *dim_names, **kwargs):
        """
        Returns an ordered dictionnary of measures from the cube, structured following *dim_names*. For example :

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

        If *full=False*, only the measures for which all dimensions in *dim_names* are fixed will be returned. For example : ::

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

        dim_names = list(dim_names)
        next_dim_name = self._pop_first_dim(dim_names)

        if next_dim_name:
            #dictionnary containing *measure_dict* of the subcubes
            subcubes_dict = odict()
            for subcube in self.subcubes(next_dim_name):
                dim_value = subcube.constraint[next_dim_name]
                subcubes_dict[dim_value] = subcube.measure_dict(*dim_names, **kwargs)
            if full:
                returned_dict['measure'] = self.measure()
                returned_dict['subcubes'] = subcubes_dict
            else:
                returned_dict = subcubes_dict
        else:
            returned_dict['measure'] = self.measure()
        return returned_dict

    def measure_list(self, *dim_names):
        """
        Returns a multidimensionnal list of measures from the cube, structured following *dim_names*. For example : ::

            >>> cube(['dim1', 'dim2']).measures_list('dim2', 'dim1') == [
            ...     [measure_11_21, measure_11_22, , measure_11_2N],
            ...     [measure_12_21, measure_12_22, , measure_12_2N],
            ... 
            ...     [measure_1N_21, measure_1N_22, , measure_1N_2N]
            ... ] # Where <measure_AB_CD> means measure of cube with dimA=valB and dimC=valD
        """
        returned_list = []

        dim_names = list(dim_names)
        next_dim_name = self._pop_first_dim(dim_names)
        
        #We check if there is still dimensions in *dim_names*,
        #otherwise we return a list of measures. 
        if dim_names:
            for subcube in self.subcubes(next_dim_name):
                returned_list.append(subcube.measure_list(*dim_names))
        elif next_dim_name:
            for subcube in self.subcubes(next_dim_name):
                returned_list.append(subcube.measure())
        return returned_list

    def get_sample_space(self, dim_name):
        """
        :returns: list -- the sample space for the cube for the dimension *dim_name*. 
        """
        return self.dimensions[dim_name].get_sample_space()

    @property
    def constraint(self):
        """
        dict -- a dictionnary *dimension_name: constraint_value*. The dimensions that are not constrained are not in this dictionnary.
        """
        constraint_dict = {}
        for dimension in self.dimensions.values():
            if dimension.constraint:
                constraint_dict[dimension.name] = dimension.constraint
        return constraint_dict

    def _pop_first_dim(self, dim_names, free_only=False):
        """
        Pops the first dimension name from *dim_names*.

        :param free_only: if True, only the dimensions that are not constrained will be poped.

        :returns: The poped dimension name, or None if there is no dimension name to pop.
        """
        for index, dim_name in enumerate(dim_names):
            if dim_name not in self.dimensions:
                raise ValueError("invalid dimension %s" % dim_name)
            #if dimension is constrained we don't need to iterate for it.
            if free_only and dim_name in self.constraint:
                continue
            else:
                return dim_names.pop(index)
        return None

    def __copy__(self):
        dimensions = copy.copy(self.dimensions)
        cube_copy = self.__class__()
        cube_copy.dimensions = dimensions
        return cube_copy

    def __repr__(self):
        constr_dimensions = sorted(["%s=%s" % (dim, value) for dim, value in self.constraint.iteritems()])
        free_dimensions = sorted(list(set(self.dimensions) - set(self.constraint)))
        return 'Cube(%s)' % ", ".join(free_dimensions + constr_dimensions)

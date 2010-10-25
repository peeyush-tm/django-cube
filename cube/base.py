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
import copy

class BaseDimension(object):
    """
    The base class for a dimension of a cube.

    Kwargs:
        sample_space (iterable|callable): The sample space of the dimension to create.
    """

    def __init__(self, sample_space=[]):
        """
        """
        self._name = ""
        self.sample_space = sample_space
        self._constraint = None

    @property
    def name(self):
        """
        Returns:
            str. The name of the dimension.
        """
        return self._name

    @property
    def constraint(self):
        """
        Returns:
            object. The value to which the dimension is constrained
        """
        return self._constraint

    @constraint.setter
    def constraint(self, value):
        """
        Setter for the property :meth:`constraint`.

        Args:
            value (object): The value to set the dimension's constraint to.
        """
        self._constraint = value

    @property
    def pretty_constraint(self):
        """
        Returns:
            str. A pretty string representation of the constraint's value 
        """
        return self.constraint

    def get_sample_space(self, sort=False):
        """
        Kwargs:
            sort (bool): whether to sort or not the sample space returned

        Returns:
            list. The sample space for the calling dimension. If the dimension is constrained, the sample space is only the constraint value.
        """
        sample_space = [self.constraint] or self.sample_space
        if sort:
            return self._sort_sample_space(sample_space)
        else:
            return sample_space

    def _sort_sample_space(self, sample_space):
        """
        Args:
            sample_space (iterable). The sample space to sort, can be any iterable.

        Returns:
            list. The sample space sorted.
        """
        return sorted(list(sample_space))

class BaseCubeOptions(object):
    """
    'Container' object for meta informations on a cube class. 
    """
    def __init__(self, options):
        self.dimensions = None

class BaseCubeMetaclass(type):
    """
    Metaclass for :class:`BaseCube`.
    """
    def __new__(cls, name, bases, attrs):
        #We gather in *dimensions* all the dimensions found in *attrs*
        dimensions = {}
        attrs_copy = copy.copy(attrs)
        for attr_name, attr_value in attrs_copy.iteritems():
            if isinstance(attr_value, BaseDimension):
                dimensions[attr_name] = attr_value
                attr_value._name = attr_name
                #we don't want the dimension to be directly an attribute of the new class
                del attrs[attr_name]

        new_class = super(BaseCubeMetaclass, cls).__new__(cls, name, bases, attrs)
        #meta informations on a cube class
        meta = getattr(new_class, 'Meta', None)
        if meta:
            del new_class.Meta
        new_class._meta = BaseCubeOptions(meta)

        #We take the first base class that is a subclass of *BaseCube*.
        if name == 'BaseCube':
            parent_cube_class = None
        else:
            parent_cube_class = filter(lambda base: issubclass(base, BaseCube), bases)[0]
        #If there is one, we force inheritage of some attributes from the *parent_cube_class*
        parent_dimensions = copy.deepcopy(parent_cube_class._meta.dimensions)\
            if parent_cube_class else {}
        parent_dimensions.update(dimensions)
        dimensions = parent_dimensions
        new_class._meta.dimensions = dimensions

        return new_class
        
class BaseCube(object):
    """
    The base class for a cube.
    
    .. todo:: clarify get_sample_space and sorting
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
    
    @staticmethod
    def sort_key(coordinates):
        """
        This method can be overriden for custom sorting of the cube's sample space. This will result in a custom order, when using every method that iterates on a cube for measures or subcubes.

        Args:
            coordinates (dict). The coordinates to generate a sorting key from. The format of *coordinates* is *{'dim_name1': val1', 'dim_name2': val2, ...}*.

        Returns:
            object. A key generated to sort the sample space of the cube.
        """
        raise NotImplementedError

    def subcubes(self, *dim_names):
        """
        Returns:
            iterator. A sorted iterator on all the sucubes with dimensions in *dim_names* constrained. It is sorted according to :meth:`sort_key`.For example :

            >>> class MyCube(Cube):
            ...     name = Dimension(sample_space=['John', 'Jack'])
            ...     instrument = Dimension(sample_space=['Trumpet'])
            ...     age = Dimension(sample_space=[14, 89])
            ...
            ...     @staticmethod
            ...     def sort_key(coordinates):
            ...         return ''\\
            ...             + str(coordinates.get('name', ''))\\
            ...             + str(coordinates.get('instrument', ''))\\
            ...             + str(coordinates.get('age', ''))

            >>> list(MyCube().subcubes('name', 'instrument'))
            [Cube(age, instrument='Trumpet', name='Jack'), Cube(age, instrument='Trumpet', name='John')]

        .. note:: If one of the dimensions whose name passed as parameter is already constrained in the calling cube, it is not considered as an error.
        """
        dim_names = list(dim_names)
        #sublist of *dim_names*, with only dimensions that are not yet constrained
        free_dim_names = []
        free_dim_name = self._pop_first_dim(dim_names, free_only=True)
        while (free_dim_name):
            free_dim_names.append(free_dim_name)
            free_dim_name = self._pop_first_dim(dim_names, free_only=True)

        #if no free dimension, the cube is completely constrained, no need to get further
        if not free_dim_names:
            yield copy.deepcopy(self)
            raise StopIteration

        #else, we get and sort the cube's sample space
        sample_space = self.get_sample_space(*free_dim_names)
        try:
            sample_space = sorted(sample_space, key=self.sort_key)
        except NotImplementedError:
            pass

        #and yield the subcubes
        for value in sample_space:
            yield self.constrain(**value)
        raise StopIteration

    def constrain(self, **extra_constraint):
        """
        Updates the calling cube's *constraint* with *extra_constraint*. Example :

            >>> cube = MyCube(queryset)
            >>> subcube = cube.constrain(dimensionA=2)
            >>> cube ; subcube
            MyCube(dimensionA)
            MyCube(dimensionA=2)

        Returns:
            Cube. A copy of the calling cube, with the updated constraint.
        """
        cube_copy = copy.deepcopy(self)
        dimensions = cube_copy.dimensions

        for dim_name, value in extra_constraint.iteritems():
            try:
                dimensions[dim_name].constraint = value
            except KeyError:
                raise ValueError("invalid dimension %s" % dim_name)
        
        return cube_copy

    def measure(self, **coordinates):
        """
        Returns:
            object. The measure on the cube at *coordinates*. For example :
            
                >>> cube.measure(dim1=val1, dim2=val2, dimN=valN)
                12.98

            If *coordinates* is empty, the measure returned is calculated on the whole cube. 
        """
        raise NotImplementedError

    def get_sample_space(self, *dim_names, **kwargs):
        """
        Returns:
            list. The sample space for the cube for the dimensions *dim_names*.
        
        Kwargs:
            format (str). The format of the sample space returned :
                - 'dict': [{'dim1': val11, ..., 'dimN': val1N}, ..., {'dim1': valN1, ..., 'dimN': valNN}]
                - 'tuple': [(val11, ... val1N), ..., (valN1, ..., valNN)] ; the values in the tuples map to dimensions names in *dim_names*.
                - 'flat': [val1, ..., valN] ; only available if there is ONE dimension name passed as a parameter
        """
        format = kwargs.get('format', 'dict')
        if format == 'flat' and len(dim_names) > 1:
            raise ValueError('format="flat" is valid if there is only one dimension name passed to the function')

        dim_names = list(dim_names)
        #name of the first dimension in the list
        dim_name = self._pop_first_dim(dim_names)
        #cube's sample space : [{dim1: val11, dim2: val21, ...}, ...,  {...}]
        sample_space = []

        #We fill in cube's sample space, by finding all the combination
        #possible of all dimensions' sample spaces.
        while dim_name:
            new_sample_space = []
            if sample_space:
                for old_value in sample_space:
                    for extra_value in self.dimensions[dim_name].get_sample_space():
                        if format == 'dict':
                            new_value = dict(old_value)
                            new_value.update({dim_name: extra_value})
                            new_sample_space.append(new_value)
                        elif format == 'tuple':
                            new_sample_space.append(old_value + (extra_value,))
                sample_space = new_sample_space
            else:
                if format == 'dict':
                    sample_space = [{dim_name: value} for value in self.dimensions[dim_name].get_sample_space()]
                elif format == 'tuple':
                    sample_space = [(value,) for value in self.dimensions[dim_name].get_sample_space()]
                elif format == 'flat':
                    sample_space = list(self.dimensions[dim_name].get_sample_space())
            dim_name = self._pop_first_dim(dim_names)
        return sample_space

    @property
    def constraint(self):
        """
        Returns:
            dict. A dictionnary of pairs *(dimension_name, constraint_value)*. Dimensions that are not constrained do not appear in this dictionnary.
        """
        constraint_dict = {}
        for dimension in self.dimensions.values():
            if dimension.constraint:
                constraint_dict[dimension.name] = dimension.constraint
        return constraint_dict

    def _pop_first_dim(self, dim_names, free_only=False):
        """
        Pops the first dimension name from *dim_names*.

        Kwargs:
            free_only (bool): if True, only the dimensions that are not constrained will be poped.

        Returns:
            str|None. The poped dimension name, or None if there is no dimension name to pop.
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

    def __repr__(self):
        constr_dimensions = sorted(["%s=%s" % (dim, value) for dim, value in self.constraint.iteritems()])
        free_dimensions = sorted(list(set(self.dimensions) - set(self.constraint)))
        return 'Cube(%s)' % ", ".join(free_dimensions + constr_dimensions)

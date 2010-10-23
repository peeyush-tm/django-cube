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

from .utils import odict

class CubeQueryMixin(object):
    """
    Mixin class whose purpose is to separate querying of measures, from the cube logic itself. 
    """

    def measure_dict(self, *dim_names, **kwargs):
        """
        Returns: 
            dict. An ordered dictionnary of measures from the cube, structured following *dim_names*. For example :

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
        Returns:
            list. A multidimensionnal list of measures from the cube, structured following *dim_names*. For example :

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

    def table_helper(self, *dim_names):
        """
        A helper function to build a table from a cube. It takes two dimensions, and creates a dictionnary from it.  

        Args:
            dim_names ((str, str)): the two dimension's names. 

        Returns:
            dict. A dictionnary containing the following variables :

                - col_names: list of tuples *(<column name>, <column pretty name>)*
                - row_names: list of tuples *(<row name>, <row pretty name>)*
                - cols: list of columns, as *[{'name': col_name, 'pretty_name': col_pretty_name, 'values': [measure1, measure2, , measureN], 'overall': col_overall}]*
                - rows: list of columns, as *[{'name': row_name, 'pretty_name': row_pretty_name, 'values': [measure1, measure2, , measureN], 'overall': row_overall}]*
                - row_overalls: list of measure on whole rows, therefore the measure is taken on the row dimension, with *row_name* as value
                - col_overalls: list of measure on whole columns, therefore the measure is taken on the column dimension, with *col_name* as value
                - col_dim_name: the dimension on which the columns are calculated
                - row_dim_name: the dimension on which the rows are calculated
                - overall: measure on the whole cube
        """
        col_names = []
        row_names = []
        cols = []
        rows = []
        row_overalls = []
        col_overalls = []
        col_dim_name = str(dim_names[0])
        row_dim_name = str(dim_names[1])
        overall = None

        #columns variables in the context
        for col_subcube in self.subcubes(col_dim_name):
            col_dimension = col_subcube.dimensions[col_dim_name]
            #column level variables
            col_names.append((
                col_dimension.constraint,
                col_dimension.pretty_constraint
            ))
            col_overalls.append(col_subcube.measure())
            col = {
                'values': [],
                'overall': col_subcube.measure(),
                'name': col_dimension.constraint, 
                'pretty_name': col_dimension.pretty_constraint,
            }
            #cell level variables
            for cell_subcube in col_subcube.subcubes(row_dim_name):
                col['values'].append(cell_subcube.measure())
            cols.append(col)

        #rows variables in the context
        for row_subcube in self.subcubes(row_dim_name):
            row_dimension = row_subcube.dimensions[row_dim_name]
            #row level variables
            row_names.append((
                row_dimension.constraint,
                row_dimension.pretty_constraint
            ))
            row_overalls.append(row_subcube.measure())
            row = {
                'values': [],
                'overall': row_subcube.measure(),
                'name': row_dimension.constraint, 
                'pretty_name': row_dimension.pretty_constraint,
            }
            #cell level variables
            for cell_subcube in row_subcube.subcubes(col_dim_name):
                row['values'].append(cell_subcube.measure())
            rows.append(row)

        #context dict
        return {
            'col_names': col_names,
            'row_names': row_names,
            'cols': cols,
            'rows': rows,
            'row_overalls': row_overalls,
            'col_overalls': col_overalls,
            'col_dim_name': col_dim_name,
            'row_dim_name': row_dim_name,
            'overall': self.measure(),
        }

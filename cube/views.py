from django.views.generic.simple import direct_to_template

def table_from_cube_context(cube, dimensions):
    """
    A helper function to build a table from a cube. It takes a cube and two dimensions, and creates a dictionnary from it.  

    Args:
        cube (Cube): the cube to create the table from.
        dimensions ((str, str)): the two dimension's names. 

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
            - cube: the cube passed as a parameter to the tag.
    """
    col_names = []
    row_names = []
    cols = []
    rows = []
    row_overalls = []
    col_overalls = []
    col_dim_name = str(dimensions[0])
    row_dim_name = str(dimensions[1])
    overall = None

    #columns variables in the context
    for col_subcube in cube.subcubes(col_dim_name):
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
    for row_subcube in cube.subcubes(row_dim_name):
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
        'overall': cube.measure(),
        'cube': cube
    }

def table_from_cube(request, cube, dimensions, **kwargs):
    """
    A view built on *direct_to_template*, that adds an extra_context built with :func:`table_from_cube_context`.
    """
    extra_context = table_from_cube_context(cube, dimensions)
    kwargs.setdefault('extra_context', {}).update(extra_context)
    return direct_to_template(request, **kwargs)

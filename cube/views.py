from django.shortcuts import render_to_response
from django.template import RequestContext

def table_from_cube(request, cube=None, dimensions=None, extra_context={}, template_name='table_from_cube.html'):
    """
    A view that renders *template_name* with a context built with :func:`cube.models.Cube.table_helper`.

    Kwargs:
    
        cube(Cube). The cube to build the table from.
        dimensions(list). A list ["dimension1", "dimension2"], where "dimension1" is the name of the dimension that will be used for columns, "dimension2" the name of the dimension for rows.
    """
    if not cube:
        raise TypeError('You must provide a cube.')

    if not dimensions or None in dimensions:
        raise TypeError('You must provide two dimensions, either by passing them as kwargs, or by sending them along with the request.')

    context = cube.table_helper(*dimensions)
    context["cube"] = cube
    context.update(extra_context)

    return render_to_response(template_name, context, context_instance=RequestContext(request))

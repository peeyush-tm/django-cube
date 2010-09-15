from django.views.generic.simple import direct_to_template

def table_from_cube(request, cube, dimensions, **kwargs):
    """
    A view built on *direct_to_template*, that adds an extra_context built with :func:`table_from_cube_context`.
    """
    extra_context = cube.table_helper(*dimensions)
    extra_context["cube"] = cube
    kwargs.setdefault('extra_context', {}).update(extra_context)
    return direct_to_template(request, **kwargs)

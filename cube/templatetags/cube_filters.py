from ..base import Coords
import re

from django.template.defaultfilters import register

@register.filter(name='subcube')
def subcube(cube, args):
    """
    Returns a subcube with dimensions passed as *args*. Usage : ::
    
        {{ cube|subcube:"dim1, dim2, dimn" }}
    """
    dim_list = re.split(r'\s*,\s*', args)
    try:
        return cube.subcube(dim_list)
    except ValueError:
        return cube

@register.filter(name='coords')
def coords(cube, args):
    """
    Returns the measure of the cube which is at coordinates *args*. Usage : ::
    
        {{ cube|coords:"dim1=val1, dim2=val2, dimn=valn" }}
    """
    args_dict = {}
    args_list = re.split('\s*,\s*', args)
    for index in xrange(0, len(args_list)):
        coord_value = re.split('\s*=\s*', args_list[index])
        args_dict[coord_value[0]] = coord_value[1]
    try:
        return cube[Coords(**args_dict)]
    except KeyError:
        return ""

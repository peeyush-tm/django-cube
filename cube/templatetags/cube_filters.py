from ..base import Coords
import re

from django.template.defaultfilters import register

@register.filter(name='subcube')
def subcube(cube, args):
    """
    Returns a subcube with dimensions passed as *args*. Usage : ::
    
        {{ cube|subcube:'dim1, dim2, dimn' }}
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
    
        {{ cube|coords:'dim1=type1(val1), dim2=type2(val2), dimn=typen(valn)' }}

    Example : ::
        
        {{ cube|coords:'title=str("a title"), amount=int(178)' }}
    """
    args_dict = {}
    for result in re.finditer(r"(?P<dimension>\w+)\s*=\s*(?P<type>\w+)\((?P<value>.*?)\)", args):
        try:
            exec('value = %s(%s)' % (result.group('type'), result.group('value')))
        except Exception as e:
            return ''
        else:
            args_dict[result.group('dimension')] = value

    try:
        return cube[Coords(**args_dict)]
    except KeyError:
        return ''

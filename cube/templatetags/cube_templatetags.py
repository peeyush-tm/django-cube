import re

from django.template import Node, NodeList, TemplateSyntaxError, Library

register = Library()


class SubcubesNode(Node):

    def __init__(self, cube, dimensions, subcube_var, nodelist):
        self.dimensions, self.cube = dimensions, cube
        self.subcube_var = subcube_var
        self.nodelist = nodelist

    def __repr__(self):
        return "<Subcube Node: %s by %s as %s>" % \
            (self.cube, ', '.join(self.dimensions), self.subcube_var)

    def __iter__(self):
        for node in self.nodelist:
            yield node

    def render(self, context):
        if 'subcubeloop' in context:
            parentloop = context['subcubeloop']
        else:
            parentloop = {}
        context.push()
        
        #resolve cube from context
        try:
            cube = self.cube.resolve(context, False)
        except VariableDoesNotExist:
            return ''

        nodelist = NodeList()
        # Create a subcubeloop value in the context.  We'll update counters on each
        # iteration just below.
        loop_dict = context['subcubeloop'] = {'parentloop': parentloop}
        #for i, subcube in enumerate(cube):
        for subcube in cube.subcubes(*self.dimensions):
            # Shortcuts for current loop iteration number.
            #loop_dict['counter0'] = i
            #loop_dict['counter'] = i+1
            # Reverse counter iteration numbers.
            #loop_dict['revcounter'] = len_values - i
            #loop_dict['revcounter0'] = len_values - i - 1
            # Boolean values designating first and last times through loop.
            #loop_dict['first'] = (i == 0)
            #loop_dict['last'] = (i == len_values - 1)

            context[self.subcube_var] = subcube
            for node in self.nodelist:
                nodelist.append(node.render(context))

        context.pop()
        return nodelist.render(context)


def do_subcubes(parser, token):
    """
    Use the *subcubes* template tag to loop over the subcubes of a cube. The syntax is : ::

        {% subcubes <cube> by <dimension1>[, <dimensionN>] as <subcube> %}
            ...
        {% endsubcubes %}

    Example : ::

        <ul>
        {% subcubes musician_cube by name, instrument as m_subcube %}
                <li> {{ m_subcube|getconstraint:"instrument" }}
                <ul>
                    {% subcubes m_subcube by name as i_subcube %}
                    <li>{{ i_subcube|getconstraint:"name" }} : {{ i_subcube.measure }}</li>
                    {% endfor %}
                </ul>
                </li>
        {% endsubcubes %}
        </ul>

    Would for example output : ::

        * Trumpet
            - John : 9
            - Jack : 67
            - Miles : 1
        * Saxophone
            - Jean-michel : 10
            ...
    """
    bits = token.contents.split()
    tagname = bits[0]

    if len(bits) < 6:
        raise TemplateSyntaxError("'%s' statements should have at least six"
                                  " words: %s" % (tagname, token.contents))

    by_index = 2
    if bits[by_index] != 'by':
        raise TemplateSyntaxError("'%s' statements should use the format"
                                  " '%s cube by dimension as subcube': %s" % (tagname, tagname, token.contents))
    
    as_index = -2
    if bits[as_index] != 'as':
        raise TemplateSyntaxError("'%s' statements should use the format"
                                  " '%s cube by dimension as subcube': %s" % (tagname, tagname, token.contents))

    #trim the spaces around comas, and then split the list to have all the dimensions
    dimensions = re.sub(r' *, *', ',', ' '.join(bits[by_index + 1:as_index])).split(',')
    for dim in dimensions:
        if not dim or ' ' in dim:
            raise TemplateSyntaxError("'%s' tag received an invalid argument:"
                                      " %s" % (tagname, token.contents))
    
    #name of the variable that will contain the subcube
    subcube_var = bits[-1]

    #turns the cube argument into a template.Variable
    cube = parser.compile_filter(bits[1])

    #gets all the nodes contained in the tag
    nodelist = parser.parse(('end%s' % tagname,))
    #next token is *endsubcubes* so we delete it
    parser.delete_first_token()

    return SubcubesNode(cube, dimensions, subcube_var, nodelist)

do_subcubes = register.tag("subcubes", do_subcubes)


def get_constraint(cube, dimension):
    """
    Filter to get the value of the constraint for a dimension. Use it as : ::
        
        {{ <cube>|getconstraint:'<dimension>' }}
    """
    return cube.constraint[dimension]

register.filter('getconstraint', get_constraint)

def inspect_object(obj):
    return obj.measure()
    #return '///'.join([memb + " %s" % type(getattr(obj, memb)) for memb in dir(obj)])

register.filter('my_super_unique_inspect', inspect_object)


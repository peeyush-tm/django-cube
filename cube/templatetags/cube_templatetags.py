import re

from django.template import Node, NodeList, TemplateSyntaxError, Library, Variable

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
        #resolve cube from context
        try:
            cube = self.cube.resolve(context, False)
        except VariableDoesNotExist:
            return ''

        #resolve dimensions
        dimensions = []
        for dimension in self.dimensions:
            matched = re.match('(?P<quote>"|\')(?P<literal>\w+)(?P=quote)', dimension)
            if matched:
                dimensions.append(matched.group('literal'))
            else:
                dimensions.append(Variable(dimension).resolve(context))

        #loop subcubes and render nodes
        nodelist = NodeList()
        for subcube in cube.subcubes(*dimensions):
            context[self.subcube_var] = subcube
            for node in self.nodelist:
                nodelist.append(node.render(context))

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




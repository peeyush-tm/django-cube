import re
import copy

from django.template import Node, NodeList, TemplateSyntaxError, Library, Variable, Context, VariableDoesNotExist
from django.template.loader  import get_template
from django.conf import settings

register = Library()


class TableFromCubeNode(Node):
    def __init__(self, cube, dimensions, filepath):
        self.filepath = filepath
        self.dimensions, self.cube = dimensions, cube

    def render(self, context):

        #resolve filename
        matched = re.match('(?P<quote>"|\')(?P<literal>\w+)(?P=quote)', self.filepath)
        if matched:
            filepath = matched.group('literal')
        else:
            try:
                filepath = Variable(self.filepath).resolve(context)
            except VariableDoesNotExist:
                if settings.DEBUG:
                    return "[couldn't resolve file path]"
                else:
                    return ''
        
        #resolve cube from context
        try:
            cube = self.cube.resolve(context, False)
        except VariableDoesNotExist:
            if settings.DEBUG:
                return "[couldn't resolve cube]"
            else:
                return ''

        #resolve dimensions
        dimensions = []
        for dimension in self.dimensions:
            matched = re.match('(?P<quote>"|\')(?P<literal>\w+)(?P=quote)', dimension)
            if matched:
                dimensions.append(matched.group('literal'))
            else:
                try:
                    dimensions.append(Variable(dimension).resolve(context))
                except VariableDoesNotExist:
                    if settings.DEBUG:
                        return "[couldn't resolve dimension]"
                    else:
                        return ''

        #build context
        try:
            extra_context = cube.table_helper(*dimensions)
            extra_context['cube'] = cube
        except ValueError, e:
            if settings.DEBUG:
                return "[%s]" % e
            else:
                return ''

        #rendering template
        try:
            new_context = copy.copy(context)
            new_context.update(extra_context)
            t = get_template(filepath)
            c = Context(new_context)
            return t.render(c)
        except TemplateSyntaxError, e:
            if settings.TEMPLATE_DEBUG:
                raise
            return ''
        except:
            return '' # Fail silently for invalid included templates.


def do_tablefromcube(parser, token):
    """
    Inclusion tag to render a table using a defined template. Usage : ::
    
        {% tablefromcube <cube> by <dimension1>, <dimension2> using <template_name> %}

    For example : ::
    
        {% tablefromcube my_cube by some_dimension, "some_other_dimension" using "mytable.html" %}

    The context with which this template is rendered contains the variables :

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
    bits = token.contents.split()

    tagname = bits[0]
    by_index = 2
    using_index = 5
    filepath_index = -1

    if not len(bits) == 7:
        raise TemplateSyntaxError("'%s' tag should have seven words: %s" % (tagname, token.contents))
    
    if not bits[by_index] == 'by' or not bits[using_index] == 'using':
        raise TemplateSyntaxError("'%s' invalid syntax, 'by' or 'using'"
                                  "not at the expected position %s" % (tagname, token.contents))

    #trim the spaces around comas, and then split the list to have all the dimensions
    dimensions = re.sub(r' *, *', ',', ' '.join(bits[by_index + 1:using_index])).split(',')
    for dim in dimensions:
        if not dim or ' ' in dim:
            raise TemplateSyntaxError("'%s' tag received an invalid argument:"
                                      " %s" % (tagname, token.contents))

    #turns the cube argument into a template.Variable
    cube = parser.compile_filter(bits[1])

    return TableFromCubeNode(cube, dimensions, bits[filepath_index])
do_tablefromcube = register.tag('tablefromcube', do_tablefromcube)


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
                dimensions.append(str(matched.group('literal')))
            else:
                try:
                    dimensions.append(str(Variable(dimension).resolve(context)))
                except VariableDoesNotExist:
                    return ''

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
        {% subcubes musician_cube by "instrument" as m_subcube %}
                <li> {{ m_subcube|prettyconstraint:"instrument" }}
                <ul>
                    {% subcubes m_subcube by "firstname" as i_subcube %}
                    <li>{{ i_subcube|prettyconstraint:"firstname" }} : {{ i_subcube.measure }}</li>
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


def prettyconstraint(cube, dim_name):
    """
    Filter to get the value of the constraint for a dimension. Use it as : ::
        
        {{ cube|prettyconstraint:'dimension_name' }}
    """
    return cube.dimensions[dim_name].pretty_constraint

register.filter('prettyconstraint', prettyconstraint)




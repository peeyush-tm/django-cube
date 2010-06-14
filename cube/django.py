from base import BaseCube, BaseDimension

class Cube(BaseCube):
    """
    A cube that can calculate lists of measures for a queryset, on several dimensions.
    """
    def __init__(self, dimensions, queryset, aggregation, constraint={}, sample_space={}):
        """
        :param dimensions: a list of attribute names or :class:`Dimension` which represent the free dimensions of the cube. All Django nested field lookups are allowed. For example on a model `Person`, a possible dimension would be `mother__birth_date__in`, where `mother` would (why not?!) be foreign key to another person. You can also use two special lookups: *absmonth* and *absday* which both take :class:`datetime` or :class:`date`, and represent absolute months or days. E.g. To search for November 1986, you would have to use *"date__month=11, date__year=1986"*, instead you can just use *"date__absmonth=date(1986, 11, 1)"*.
        :param queryset: the base queryset from which the cube's sample space will be extracted.
        :param aggregation: an aggregation function. must have the following signature `def agg_func(queryset)`, and return a measure on the queryset.
        :param constraint: {*dimension's name*: *value*} -- a constraint that reduces the sample space of the cube.
        :param sample_space: {*dimension's name*: *sample_space*} -- specifies the sample space of *dimension*. If it is not specified, then default sample space is all the values that the dimension takes on the queryset.  
        """
        super(BaseCube, self).__init__(dimensions, aggregation, constraint={}, sample_space={})
        self.queryset = queryset

    @staticmethod
    def _to_dimensions(composite_list):
        """
        Takes a list of both :class:`Dimension` objects and string, and returns a set of :class:`Dimension` objects. 
        """
        dimensions = dict()
        for dimension in composite_list:
            if isinstance(dimension, str):
                dimensions[dimension] = Dimension(dimension)
            elif isinstance(dimension, Dimension):
                dimensions[dimension] = copy.copy(dimension)
            else:
                raise TypeError('\'%s\' of type %s is not an appropriate dimension for a cube' % (dimension, type(dimension)))
        return dimensions

    @staticmethod
    def _format_constraint(constraint):
        """
        Formats a dictionnary of constraint to make them Django-orm-compatible 
        """
        constraint_copy = copy.copy(constraint)
        for dimension, value in constraint.iteritems():
            lookup_list = re.split('__', dimension)
            if (isinstance(value, date) or isinstance(value, datetime)) and lookup_list[-1] in ['absmonth', 'absday']:
                base_lookup = ''
                for lookup_value in lookup_list[:-1]:
                    base_lookup += lookup_value + '__'

                if lookup_list[-1] == 'absmonth':
                    del constraint_copy[dimension]
                    constraint_copy[base_lookup + 'month'] = value.month
                    constraint_copy[base_lookup + 'year'] = value.year
                elif lookup_list[-1] == 'absday':
                    del constraint_copy[dimension]
                    constraint_copy[base_lookup + 'day'] = value.day
                    constraint_copy[base_lookup + 'month'] = value.month
                    constraint_copy[base_lookup + 'year'] = value.year

        return constraint_copy

    def __copy__(self):
        """
        Returns a shallow copy of the cube.
        """
        queryset = copy.copy(self.queryset)
        sample_space = copy.copy(self.sample_space)
        constraint = copy.copy(self.constraint)
        aggregation = self.aggregation
        return Cube(dimensions, queryset, aggregation, constraint=constraint, sample_space=sample_space)

    def _measure(self):
        """
        Calculates and returns the measure on the cube.
        """
        constraint = self._format_constraint(self.constraint)
        return self.aggregation(self.queryset.filter(**constraint))

class Dimension(BaseDimension):

    def __init__(self, field, queryset=None, name=None, sample_space=None):
        super(Dimension, self).__init__(field, queryset, name, sample_space)
        self.queryset = queryset
        self.sample_space = sample_space or self._default_sample_space()
    
    def __copy__(self):
        return Dimension(self.field, self.queryset, self.name, self.sample_space)

    def _default_sample_space(self):
        """
        Returns the default sample space for the calling *dimension*, which is all the values taken by *dimension* in the queryset.
        
        .. todo:: rewrite prettier
        """
        sample_space = []
        lookup_list = re.split('__', self.field)

        if len(lookup_list) == 1:
            field = self.queryset.model._meta.get_field_by_name(lookup_list[0])[0]
            #if ForeignKey, we get all distinct objects of foreign model
            if type(field) == ForeignKey:
                sample_space = field.related.parent_model.objects.distinct()
            else:
                sample_space = self.queryset.values_list(lookup_list[0], flat=True).distinct()

        else:
            queryset = self.queryset

            #we assume first item is always a field_name
            key = lookup_list.pop(0)
            
            #we loop over the rest
            next_key = lookup_list.pop(0)
    
            #For the field lookup, we just assume that a 'month', 'day' or 'year' lookup is always terminal,
            #same thing for a field that is not a foreign key.
            while (key):

                #TODO this is totally wrong ! What if there is a field called 'month', 'year', ... ? Should introspect model._meta ?
                if next_key in ['day', 'month', 'year']:
                    for date in queryset.dates(key, next_key):
                        sample_space.append(getattr(date, next_key))
                    break
                elif next_key in ['absday', 'absmonth']:
                    query_key = {'absday': 'day', 'absmonth': 'month'}[next_key]
                    for date in queryset.dates(key, query_key):
                        sample_space.append(date)
                    break 
                else:
                    field = queryset.model._meta.get_field_by_name(key)[0]
                    #if ForeignKey, we get all distinct objects of foreign model
                    if type(field) == ForeignKey:
                        sample_space = queryset = field.related.parent_model.objects.distinct()
                    #else, we just return values
                    else:
                        sample_space = queryset.values_list(key, flat=True).distinct()
                        break

                key = next_key
                try:
                    next_key = lookup_list.pop(0)
                except IndexError:
                    next_key = None

        return set(sample_space)

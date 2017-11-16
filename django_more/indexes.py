""" Define custom index types """
from django.db.models import Index, Q
from django.db import DEFAULT_DB_ALIAS

__all__ = ['PartialIndex']


class PartialIndex(Index):
    suffix = "par"

    def __init__(self, *args, fields=[], name=None, **kwargs):
        self.q_filters = [arg for arg in args if isinstance(arg, Q)]
        if kwargs:
            self.q_filters.extend([Q(**{kwarg: val}) for kwarg, val in kwargs.items()])
        super().__init__(fields, name)

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        self.make_qs_compatible()
        args += tuple(self.q_filters)
        return path, args, kwargs

    @staticmethod
    def get_where_sql(query):
        where, w_params = query.get_compiler(DEFAULT_DB_ALIAS).compile(query.where)
        return " WHERE {}".format(where % (*w_params,))

    def get_query(self, model):
        return model.objects.filter(*self.q_filters).query

    def get_sql_create_template_values(self, model, schema_editor, using):
        parameters = super().get_sql_create_template_values(model, schema_editor, using=using)
        # Create a queryset using the supplied filters to validate and generate WHERE
        query = self.get_query(model)
        # Access query compiler for WHERE directly
        if query.where:
            parameters["extra"] = self.get_where_sql(query)
        return parameters

    def make_qs_compatible(self):
        if not hasattr(Q, "deconstruct"):
            for q in [qf for qf in self.q_filters if isinstance(qf, Q)]:
                q.__class__ = Qcompat

    # Almost identical to default implementation but adds WHERE to hashing
    def set_name_with_model(self, model):
        table_name = model._meta.db_table
        column_names = [model._meta.get_field(field_name).column for field_name, order in self.fields_orders]
        column_names_with_order = [
            (('-%s' if order else '%s') % column_name)
            for column_name, (field_name, order) in zip(column_names, self.fields_orders)
        ]
        hash_data = [table_name] + column_names_with_order + [self.suffix] + [self.get_where_sql(self.get_query(model))]
        self.name = '%s_%s_%s' % (
            table_name[:11],
            column_names[0][:7],
            '%s_%s' % (self._hash_generator(*hash_data), self.suffix),
        )
        assert len(self.name) <= self.max_name_length, (
            'Index too long for multiple database support. Is self.suffix '
            'longer than 3 characters?'
        )
        self.check_name()

    def __eq__(self, val):
        if isinstance(val, PartialIndex):
            # Use cheap repr() comparison on deconstruction to check if the same
            return repr(self.deconstruct()) == repr(val.deconstruct())


# This feature is not present in Django 1.11 but is required for deconstruction of
#  partial indexes. So if not present when needed, the Qs are wrapped in this
class Qcompat(Q):

    def __init__(self, *args, **kwargs):
        connector = kwargs.pop('_connector', None)
        negated = kwargs.pop('_negated', False)
        super(Q, self).__init__(children=list(args) + list(kwargs.items()), connector=connector, negated=negated)

    def deconstruct(self):
        path = '%s.%s' % (self.__class__.__module__, self.__class__.__name__)
        args, kwargs = (), {}
        if len(self.children) == 1 and not isinstance(self.children[0], Q):
            child = self.children[0]
            kwargs = {child[0]: child[1]}
        else:
            args = tuple(self.children)
            kwargs = {'_connector': self.connector}
        if self.negated:
            kwargs['_negated'] = True
        return path, args, kwargs

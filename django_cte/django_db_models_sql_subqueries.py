from types import MethodType
from collections import OrderedDict
from django.db.models.sql.subqueries import *
from django.db.models.sql.query import Query
from functools import partial


__all__ = [
    'LiteralQuery', 'WithQuery', 'InsertReturningQuery', 'UpdateReturningQuery']


class UpdateReturningQuery(UpdateQuery):
    compiler = 'SQLUpdateReturningCompiler'

    def clone(self, klass=None, **kwargs):
        clone = super().clone(klass, **kwargs)
        clone.values = self.values
        return clone


class InsertReturningQuery(InsertQuery):
    compiler = 'SQLInsertReturningCompiler'

    def clone(self, klass=None, **kwargs):
        return super().clone(
            klass,
            fields=self.fields,
            objs=self.objs,
            raw=self.raw,
            **kwargs)

    def get_return_fields(self):
        return self.values_select, []


class InsertSelectQuery(Query):
    compiler = 'SQLInsertSelectCompiler'

    def clone(self, klass=None, **kwargs):
        return super().clone(
            klass,
            fields=self.fields,
            objs=self.objs,
            raw=self.raw,
            **kwargs)


class CTEQuery(Query):
    compiler = 'SQLCTESelectCompiler'


def _list_difference(source, subtract):
    return (item for item in source if item not in subtract)


class WithQuery:
    compiler = 'SQLWithCompiler'

    def __new__(cls, base_query, *args, **kwargs):
        # Clone functionality of base query via inheritance
        klass = base_query.__class__
        if klass != cls:
            klass = cls.clone_class(klass)
        self = super.__new__(klass, *args, **kwargs)
        return self

    def __init__(self, base_query, *args, **kwargs):
        self.base_query = base_query
        self.queries = []
        self.join_queries = []

        # Bypass methods
        # self.set_values = partial(self.base_query.set_values)

    def results_iter(self, results=None):
        return super().results_iter(results)

    def add_with(self, with_query):
        if hasattr(with_query, "queries"):
            self.queries.extend(_list_difference(with_query.queries, self.queries))
        if with_query not in self.queries:
            self.queries.append(with_query)

    def prepare_queries(self):
        # Alias every attached/with query uniquely
        for i, query in enumerate(self.queries, 1):
            query.with_alias = "cte_{}".format(i)
        self.set_with_tables()
        # Update extra tables on all child queries
        for query in (q for q in self.queries if hasattr(q, "set_with_tables")):
            query.set_with_tables()

    def add_annotation(self, annotation, *args, **kwargs):
        # Add details of parent query to expressions in annotation
        for expr in annotation.flatten():
            if hasattr(expr, "set_parent_query"):
                expr.set_parent_query(self)
        return super().add_annotation(annotation, *args, **kwargs)

    """
    @property
    def with_alias(self):
        return self.base_query.with_alias

    @with_alias.setter
    def with_alias(self, value):
        self.base_query.with_alias = value
    """

    def add_with_join(self, query):
        # Adds a CTE query to the extra_tables set
        if query not in self.join_queries:
            self.join_queries.append(query)

    def set_with_tables(self):
        # Clear any cte references and ensure all are added
        self.extra_tables = tuple([
            table_alias
            for table_alias in self.extra_tables
            if not table_alias.startswith("cte_")
        ] + [
            query.with_alias
            for query in self.join_queries])

    def clone(self, klass=None, **kwargs):
        if klass != self.cls:
            klass = self.clone_class(klass)
        return super.clone(
            klass=klass,
            join_queries=self.join_queries[:],
            queries=self.queries[:],
            **kwargs)

    @classmethod
    def clone_class(cls, klass):
        return type(
            cls.__name__ + "_with_" + klass.__name__,
            (klass, ),
            cls)


class LiteralQuery(Query):
    compiler = 'SQLLiteralCompiler'
    enum_field = None
    values_select = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields = None
        self.objs = []

    def set_values(self, field_names):
        self.values_select = tuple(field_names)
        if self.model:
            self.fields = [self.model._meta.get_field(field_name) for field_name in field_names]

    def clone(self, klass=None, **kwargs):
        return super().clone(
            klass,
            fields=self.fields,
            objs=self.objs,
            enum_field=self.enum_field,
            **kwargs)

    def clear_values(self):
        self.objs = []

    def literal_values(self, objs, fields=None):
        self.objs = objs
        if fields:
            self.fields = fields
        elif self.model:
            self.fields = self.prepare_fields(self.sample_obj)
        else:
            # No fields provided or detectable
            # Must be used with .values() etc to name fields
            pass

    @property
    def sample_obj(self):
        # To get a sample from the objs without indexing or sorting
        # Works with sets, tuples, lists, etc
        return next(iter(self.objs))

    def prepare_fields(self, obj):
        if self.model:
            opts = self.get_meta()
            if isinstance(obj, dict):
                # Detect dicts and use their keys
                return [
                    field for field in opts.concrete_fields
                    if field.name in obj]
            elif hasattr(obj, "_fields"):
                # Detect namedtuples and use their fields
                return [
                    field for field in opts.concrete_fields
                    if hasattr(obj, field.name)]
            else:
                # Is linked to a model, so take fields from there
                if len(obj) > len(opts.concrete_fields):
                    raise IndexError("Length of data row exceeds number of fields")
                # pk is skipped to simulate model instantiation behaviour
                fields = opts.concrete_fields[1:len(obj) + 1]
                return fields

    def get_columns(self):
        field_names = [self.enum_field] if self.enum_field else []
        if self.fields:
            return tuple(field_names + [field.name for field in self.fields])
        elif self.values_select:
            return tuple(field_names) + self.values_select, []
        else:
            raise AttributeError("LiteralQuery has no field names")

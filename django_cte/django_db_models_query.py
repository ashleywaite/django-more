import django
from itertools import chain
from .django_db_models_expressions import CTERef
from django.db.models import sql


class QuerySet:

    def attach(self, *querysets):
        clone = sql.WithQuery(self.query)
        for qs in querysets:
            clone.query.add_with(qs.query)
        return clone

    def as_insert(self, **kwargs):
        raise NotImplementedError("Not implemented yet")
        """
        clone = self._clone()
        clone.query = self.query.clone(sql.InsertSelectQuery)
        self._for_write = True
        clone.query.add_update_values(kwargs)
        if fields:
            fields = [self.model._meta.get_field(f) for f in fields]
        clone.query.insert_values(fields, objs, raw=raw)
        return clone
        """

    def as_update(self, **kwargs):
        clone = self._clone()
        clone.query = self.query.clone(sql.UpdateReturningQuery)
        print("clone is", type(clone))
        print("clone query is", type(clone.query))
        self._for_write = True
        clone.query.add_update_values(kwargs)
        # Clear any annotations so that they won't be present in subqueries.
        clone.query._annotations = None
        return clone

    def with_literals(self, qs):
        pass

    def ref(self, field):
        # These are not validated
        return CTERef(with_query=self.query, field_name=field)


class LiteralQuerySet(django.db.models.QuerySet):
    """ CTEs can be connected to a query to enable WITH style queries """

    def __init__(self, model=None, query=None, values=None, enum_field=None, *args, **kwargs):
        query = query or sql.LiteralQuery(model)
        super().__init__(model=model, query=query, *args, **kwargs)
        if values:
            self.append(values)
        if enum_field:
            self.enum_field(enum_field)

    def enum_field(self, field_name):
        self.query.enum_field = field_name
        return self

    def clear(self):
        self.query.clear_values()
        return self

    def append(self, values):
        self.query.literal_values(values)
        return self

    def defer(self, *fields):
        raise NotImplementedError("LiteralQuerySet does not implement defer()")

    def delete(self):
        raise TypeError("Queries with literal values can't be deleted")

    def order_by(self, *field_names):
        raise NotImplementedError("LiteralQuerySet does not implement order_by()")

    def distinct(self, *field_names):
        raise NotImplementedError("LiteralQuerySet does not implement distinct()")

    def extra(self, *args, **kwargs):
        raise NotImplementedError("LiteralQuerySet does not implement extra()")

    def reverse(self):
        raise NotImplementedError("LiteralQuerySet does not implement reverse()")

from django.db.models.expressions import RawSQL
from django.db.models import fields


class CTERef(RawSQL):
    """ Insert a reference to the CTE field in the query """

    def __init__(self, with_query, field_name, output_field=None):
        self.with_query = with_query
        self._field_name = field_name
        self.parent_query = None
        super().__init__("", [], output_field=output_field)

    def as_sql(self, compiler, connection):
        return "{}.{}".format(self.with_query.with_alias, self._field_name), []

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        # self.name = "{}.{}".format(self.cte.with_alias, self._field)
        print("query is", type(query))
        if self.parent_query:
            query = self.parent_query
        if not hasattr(query, "add_with_join"):
            raise TypeError("CTE query for field '{}' must be attached to be referenced".format(self._field_name))
        # Ensure this query is joined to the target query
        query.add_with_join(self.with_query)
        return super().resolve_expression(query, allow_joins, reuse, summarize, for_save)

    def relabeled_clone(self, relabels):
        return self

    def set_parent_query(self, query):
        print("parent set to", type(query))
        self.parent_query = query

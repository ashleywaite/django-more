from django.db.models import ExpressionWrapper


# Used by OrderByField to allow subqueries within insert statements
class BypassExpression(ExpressionWrapper):
    """ Bypass validation rules for the wrapped expression """
    contains_aggregates = False
    contains_column_references = False

    def __init__(self, expression, output_field=None):
        super().__init__(expression, output_field)


from collections import OrderedDict
from types import MethodType
from django.db.models import Field
from django.db.models import sql
from django.db.models.sql.compiler import *


class SQLCompiler:
    def get_return_fields(self):
        cols, params = [], []
        col_idx = 1
        for _, (s_sql, s_params), alias in self.select + extra_select:
            if alias:
                s_sql = self.connection.ops.quote_name(alias)
            elif with_col_aliases:
                s_sql = 'Col%d' % col_idx
                col_idx += 1
            params.extend(s_params)
            cols.append(s_sql)
        return cols, params


class SQLUpdateCompiler:
    def as_sql(self):
        """
        Create the SQL for this query. Return the SQL string and list of
        parameters.
        """
        self.pre_sql_setup()
        if not self.query.values:
            return '', ()
        qn = self.quote_name_unless_alias
        values, update_params = [], []
        for field, model, val in self.query.values:
            if hasattr(val, 'resolve_expression'):
                val = val.resolve_expression(self.query, allow_joins=False, for_save=True)
                if val.contains_aggregate:
                    raise FieldError("Aggregate functions are not allowed in this query")
            elif hasattr(val, 'prepare_database_save'):
                if field.remote_field:
                    val = field.get_db_prep_save(
                        val.prepare_database_save(field),
                        connection=self.connection,
                    )
                else:
                    raise TypeError(
                        "Tried to update field %s with a model instance, %r. "
                        "Use a value compatible with %s."
                        % (field, val, field.__class__.__name__)
                    )
            else:
                val = field.get_db_prep_save(val, connection=self.connection)

            # Getting the placeholder for the field.
            if hasattr(field, 'get_placeholder'):
                placeholder = field.get_placeholder(val, self, self.connection)
            else:
                placeholder = '%s'
            name = field.column
            if hasattr(val, 'as_sql'):
                sql, params = self.compile(val)
                values.append('%s = %s' % (qn(name), sql))
                update_params.extend(params)
            elif val is not None:
                values.append('%s = %s' % (qn(name), placeholder))
                update_params.append(val)
            else:
                values.append('%s = NULL' % qn(name))
        table = self.query.tables[0]
        result = [
            'UPDATE %s SET' % qn(table),
            ', '.join(values),
        ]
        where, params = self.compile(self.query.where)
        if self.query.extra_tables:
            from_, f_params = self.get_from_clause()
            if from_:
                result.append(" FROM {tables}".format(
                    tables=", ".join(from_)))
                params.extend(f_params)

        if where:
            result.append('WHERE %s' % where)
        return ' '.join(result), tuple(update_params + params)

    def get_from_clause(self):
        # Kludgy syntax because method declared here has wrong context for direct super()
        result, params = super(sql.compiler.SQLUpdateCompiler, self).get_from_clause()
        if len(result) <= 1:
            # ur silly ;)
            return [], tuple()
        # Strip silliness from clauses, it's ridic
        result = [clause.strip(", ") for clause in result]
        # Remove first FROM clause, UPDATE must not specify own table
        return result[1:], params


class SQLReturningMixin:
    select_setup = sql.compiler.SQLCompiler.pre_sql_setup

    def get_returning_clause(self):
        extra_select, order_by, group_by = self.select_setup()

        cols, params = [], []
        col_idx = 1
        for _, (s_sql, s_params), alias in self.select + extra_select:
            if alias:
                s_sql = '%s AS %s' % (s_sql, self.connection.ops.quote_name(alias))
            params.extend(s_params)
            cols.append(s_sql)
        return cols, tuple(params)


class SQLInsertReturningCompiler(sql.compiler.SQLInsertCompiler, SQLReturningMixin):
    def as_sql(self):
        i_sql, i_params = super().as_sql()[0]
        # Needs aliases and colnames
        if self.query.values_select:
            fields = self.query.values_select
        elif self.query.default_cols:
            fields = self.get_default_columns()
            fields = [
                sql for sql, _ in
                (self.compile(col, select_format=True) for col in fields)]
        return_, r_params = self.get_returning_clause()
        if return_:
            i_sql += " RETURNING ({fields})".format(
                fields=", ".join(return_))
            i_params += r_params
        return i_sql, i_params


class SQLInsertSelectCompiler(sql.compiler.SQLCompiler):
    def as_sql(self):
        i_sql, i_params = super().as_sql()[0]
        # Needs aliases and colnames
        if self.query.values_select:
            fields = self.query.values_select
        elif self.query.default_cols:
            fields = self.get_default_columns()
            fields = [
                sql for sql, _ in
                (self.compile(col, select_format=True) for col in fields)]
        i_sql = "INSERT INTO {insert_table} {sql} RETURNING ({fields})".format(
            into_table=self.query.into_table or self.query.model.db_table,
            sql=i_sql,
            fields=", ".join(fields)
        )
        return i_sql, i_params


class SQLUpdateReturningCompiler(sql.compiler.SQLUpdateCompiler, SQLReturningMixin):

    execute_sql = sql.compiler.SQLCompiler.execute_sql

    def as_sql(self):
        i_sql, i_params = super().as_sql()
        return_, r_params = self.get_returning_clause()
        if return_:
            i_sql += " RETURNING ({fields})".format(
                fields=", ".join(return_))
            i_params += r_params
        return i_sql, i_params

    def pre_sql_setup(self):
        pass


class SQLCTESelectCompiler:

    def __init__(self):
        self.select = []
        self.extra_select = []

    def pre_sql_setup(self):
        pass

    def get_from_clause(self):
        result, params = super().get_from_clause()
        # chop off first from
        return result[1:], params


class SQLWithCompiler:
    def __new__(cls, query, connection, using, *args, **kwargs):
        # Retype as base query
        base_compiler = query.base_query.get_compiler(using, connection).__class__
        kls = type(cls.__name__ + base_compiler.__name__, (cls, base_compiler), {})
        return object.__new__(kls)

    def __init__(self, query, connection, using):
        self.query = query
        self.connection = connection
        self.using = using
        # The select, klass_info, and annotations are needed by QuerySet.iterator()
        # these are set as a side-effect of executing the query. Note that we calculate
        # separately a list of extra select columns needed for grammatical correctness
        # of the query, but these columns are not included in self.select.
        self.get_base_compiler = self.query.base_query.get_compiler

    def as_sql(self):
        # Collect all with queries to compile
        self.query.prepare_queries()
        result, params = [], []

        for query in self.query.queries:
            # Compile only the base of nested queries instead of their tree
            if hasattr(query, "get_base_compiler"):
                compiler = query.get_base_compiler(using=self.using, connection=self.connection)
            else:
                compiler = query.get_compiler(using=self.using, connection=self.connection)
            w_sql, w_params = compiler.as_sql()

            # Needs aliases and colnames
            if hasattr(query, "get_columns"):
                fields = query.get_columns()
                fields = " ({fields})".format(
                    fields=", ".join(field for field in fields))
            else:
                fields = ""
            w_sql = "{alias}{fields} AS ({sql})".format(
                alias=query.with_alias,
                fields=fields,
                sql=w_sql
            )
            result.append(w_sql)
            params.extend(w_params)

        b_sql, b_params = self.get_base_compiler(using=self.using, connection=self.connection).as_sql()
        params.extend(b_params)

        return "WITH {withs} {base}".format(
            withs=", ".join(result),
            base=b_sql
        ), tuple(params)

    def __getattr__(self, attr):
        # Pretend to be the compiler of the base query unless it's specific to this
        base_attr = getattr(self.base_compiler, attr)
        if callable(base_attr):
            return MethodType(getattr(self.base_compiler.__class__, attr), self)
        return base_attr


class SQLLiteralCompiler(sql.compiler.SQLCompiler):
    # Lambdas to do field savvy value conversions
    field_lambdas = {
        "val": lambda f, v: f.get_prep_value(v),
        "key": lambda f, v: v,
        "rel": lambda f, v: v.id,
    }
    # Lambdas to get values from objects
    value_lambdas = {
        "dict": lambda f, o: o.get(f),
        "attr": lambda f, o: getattr(o, f),
        "list": lambda f, o: o[f],
    }

    def pre_sql_setup(self, fields, obj):
        """ Based on the model supplied, build a database value prep_map for fields
            This dict of lambdas will apply model database prep conversions as per
             Django norm.
            As literal sets are simplistic, this can be generated once instead of
             checking per object.
        """

        # Determine appropriate mapping set
        if isinstance(obj, dict):
            self.get_value = self.value_lambdas["dict"]
        elif hasattr(obj, "_fields") or all((hasattr(obj, field) for field in fields)):
            self.get_value = self.value_lambdas["attr"]
        else:
            self.get_value = self.value_lambdas["list"]

        if all(isinstance(field, Field) for field in fields):
            self.prep_mapping = OrderedDict()
            # Create type savvy field conversion list
            for field in fields:
                if not field.is_relation:
                    self.prep_mapping[field] = self.field_lambdas["val"]
                elif field.is_relation and field.name.endswith("_id"):
                    self.prep_mapping[field] = self.field_lambdas["key"]
                elif field.is_relation:
                    self.prep_mapping[field] = self.field_lambdas["rel"]
            # Promote more complex conversion iter
            self.obj_values = self.obj_values_prepped

    def obj_values(self, obj, fields):
        return [
            self.get_value(field, obj)
            for field in fields]

    def obj_values_prepped(self, obj, fields):
        return [
            self.prep_mapping[field](field, self.get_value(field.name, obj))
            for field in fields]

    def assemble_params(self, fields, objs, enum_field=None):
        if enum_field:
            yield from (value
                for row, obj in enumerate(objs, 1)
                for value in [row] + self.obj_values(obj, fields))
        else:
            yield from (value
                for obj in objs
                for value in self.obj_values(obj, fields))


    def assemble_as_sql(self, fields, objs):
        """
        Take a sequence of N fields and a sequence of M rows of values, and
        generate placeholder SQL and parameters for each field and value.
        Return a pair containing:
         * a sequence of M rows of N SQL placeholder strings, and
         * a sequence of M rows of corresponding parameter values.

        Each placeholder string may contain any number of '%s' interpolation
        strings, and each parameter row will contain exactly as many params
        as the total number of '%s's in the corresponding placeholder row.
        """
        if not objs:
            return "", []

        self.pre_sql_setup(fields, self.query.sample_obj)

        params = list(self.assemble_params(fields, objs, self.query.enum_field))

        enum_ph = ['%s'] if self.query.enum_field else []

        row_ph = "({})".format(
            ", ".join(enum_ph + [self.get_field_placeholder(field, params[i])
                for i, field in enumerate(fields)]))

        if not isinstance(fields, range):
            header_ph = "({})".format(
                ", ".join(enum_ph + ["{ph}::{type}".format(
                    ph=self.get_field_placeholder(field, params[i]),
                    type=field.db_type(self.connection))
                    for i, field in enumerate(fields)]))
        else:
            header_ph = row_ph

        sql = ", ".join([header_ph] + [row_ph] * (len(objs) - 1))

        assert (len(fields) + len(enum_ph)) * len(objs) == len(params), "Values set params not matched"
        return sql, params

    def get_field_placeholder(self, field, val):
        if hasattr(field, 'get_placeholder'):
            # Some fields (e.g. geo fields) need special munging before
            # they can be inserted.
            sql, _ = field.get_placeholder(val, self, self.connection), [val]
        else:
            # Return the common case for the placeholder
            sql = '%s'
        return sql

    def as_sql(self):
        """ Create the SQL for a set of literal values used as a CTE """
        fields = self.query.fields

        if fields and not self.query.values_select:
            # Ensure values argument for WITH compilation
            self.query.values_select = [field.name for field in fields]

        if not fields:
            fields = range(len(self.query.sample_obj))

        values_sql, params = self.assemble_as_sql(
            fields=fields, objs=self.query.objs)

        return "VALUES {}".format(values_sql), tuple(params)

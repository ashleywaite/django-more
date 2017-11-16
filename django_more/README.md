# django_more

A collection of fields and utilities to extend the functionality of Django that have no additional external dependencies.


## HashField

The HashField represents a hash of any type, that is stored as base64 in the database, and can be directly compared to hashes in base16/hex, base64, and base256/raw.

Returns an `str` subclass `HashString`, which provides additional functionality to work with hashes in a more intuitive way.

**bit_length = int**  
Raw bit length of the hash, which then determines the appropriate base16 and base64 lengths.  
ie, md5 is 128 bits, sha256 is 256 bits

**max_length = int**  
Field size (ie, _max_length_ on _Charfield_). This will default to be the size that will contain the base64 representation of the _bit_length_, but can be set to be larger to accommodate legacy data or longer atypical hashes.


## OrderByField

The `OrderByField` is a database constraint enforced field providing similar functionality to the Django _Meta.order_with_respect_to_ model option, which uses database expressions for incrementing instead of multiple queries.

It does not apply a Django _Meta.order_by_ to the model like _Meta.order_with_respect_to_ does, so query sets will not be ordered by this by default. Thus this field can be used to provide an ordering that does not affect queries and will not generate an _ORDER BY_ clause, but can be used for other purposes such as display.  
As this is a concrete field, a _Meta.order_by_ can be specified on the model to add this behaviour. ie, `order_by = ('wrt_field_1', 'wrt_field_2', 'order_by_field')`

If _unique_for_fields_ is not specified it will instead default to being a _unique_ field, acting as an ordering for the entire model.

If _unique_for_field_ is specified it will act similar to an _Meta.order_with_respect_to_ on those fields.

The default value for the field will be one greater than the existing maximum value matching the ordering set.  
Using `Count` can lead to duplicate values if records are deleted unless all records are renumbered to maintain contiguous numbering. To avoid necessitating this and allow this field to be filled on the database side, it's done via a `SubQuery` with `Max`, so record creation is a single database query and can be done in bulk.

**unique_for_fields = [str, str, ...]** (via `UniqueForFieldsMixin`)  
The list of fields that should be used similar to _Meta.order_with_respect_to_.  
All fields must be concrete as a _Meta.unique_together_ model option (for these fields and self) is generated to create the appropriate database constraint.


## PartialIndex

An `Index` implementation allowing for partial indexes to be defined based upon Django filter or Q notation. Used within the _Meta.indexes_ option on a model.

**\*args**  
`Q` objects to restrict the index generated, same as for `QuerySet.filter()`

**fields = [str, str, ...]**  
Same as for `Index`

**name = str**
Same as for `Index`

**\*\*kwargs**  
Keyword filters to restrict the index generated, same as for `QuerySet.filter()`


# Utility Classes

Various classes used by the exposed fields and functions to abstract or encapsulate necessary functionality.


## HashString (hashing.py)

An `str` subclass with additional hashing based methods and an `__eq__()` method that will attempt to coerce comparisons to hashes to the same representation. ie, allowing base64 and base16 representations of the same hash to evaluate as equal.

String representation is lowercase base16, which is the most human-friendly, while the `__repr__()` will be base64.

Bytes representation is the base256 (raw) bytes of the hash itself, and not bytes reflecting any specific representation.

The `__hash__()` of all instances is based upon the base64 representation, so two instances generated from different representations of the same hash will hash to the same, such that `set` or `dict` operations will behave in an intuitive manner.

**from_b16(str)**  
_classmethod_ that creates a new instance from a base16 string.

**from_b64(str)**  
_classmethod_ that creates a new instance from a base64 string..

**from_b256(str)**  
_classmethod_ that creates a new instance from a base256 string or raw hash in bytes.


## UniqueForFieldsMixin (mixins.py)

When this mixin is added to a field it adds an additional _unique_for_fields_ argument.

When _unique_for_fields_ is provided, an additional database constraint is added via _Meta.unique_together_ for this field and all fields specified.

As a _Meta.unique_together_ completely covers the utility of the _unique_ field option, if _unique_for_fields_ is provided, it will remove _unique_ if set on the field.


## BypassExpression (expressions.py)

Wraps an `Expression` in the same was as `ExpressionWrapper` but prevent validation from flagging the expression as containing column references or aggregates.

Most useful to allow some expressions to be used in _INSERT_ statements that are otherwise rejected by Django for being too difficult to validate.  
Without Django validating any references or aggregates within the expression, there are no warnings about these if they are invalid or cannot be resolved.

# django_more
A collection of fields and classes to extend the functionality of Django that have no additional external dependencies.

```python
import hashlib
from django.db import models
from django_more import HashField, OrderByField, PartialIndex

class Evidence(models.Model):
    # What we found!
    name = models.CharField(max_length=30)
    location = models.CharField(max_length=30)
    # Field to store an md5 of the evidence
    md5 = HashField(bit_length=128, null=True)
    # Field to store sha256, but allows longer HashStrings
    sha256 = HashField(bit_length=256, max_length=64, null=True)
    # Order with respect to name and location
    order = OrderByField(unique_for_fields=['name', 'location'])
    class Meta:
        indexes = [
            # Index fields md5 and sha256 where name is 'Knife' or starts with 'Sharp'
            PartialIndex(Q(name='Knife') | Q(name__startswith='Sharp'), fields=['md5', 'sha256']),
            # Index field md5 where location is 'Library'
            PartialIndex(fields=['md5'], location='Library')
        ]
```

[HashField]: fields/hashfield.py "Link to source"
[OrderByField]: fields/orderbyfield.py "Link to source"
[PartialIndex]: indexes.py "Link to source"
[HashString]: hashing.py "Link to source"
[UniqueForFieldsMixin]: mixins.py "Link to source"
[BypassExpression]: expressions.py "Link to source"
[Options.order_with_respect_to]: https://docs.djangoproject.com/en/1.11/ref/models/options/#order-with-respect-to "Django documentation: Model options section for order_with_respect_to (1.11)"
[Django field lookups]: https://docs.djangoproject.com/en/1.11/topics/db/queries/#field-lookups-intro "Django documentation: Field lookups intoduction (1.11)"
[Django Q lookups]: https://docs.djangoproject.com/en/1.11/topics/db/queries/#complex-lookups-with-q-objects "Django documentation: Complex lookups with Q objects (1.11)"

## HashField
[HashField][] represents a hash of any type, that is stored as base64 in the database, and can be directly compared to hashes in base16/hex, base64, and base256/raw.

Returns an `str` subclass `HashString`, which provides additional functionality to work with hashes in a more intuitive way.

```python
text = 'The quick brown fox jumps over the lazy dog'

# Hash text with md5
md5_digest = hashlib.md5(bytes(text, encoding='utf-8')).digest()

# Store hash directly
record = Evidence(md5=md5_digest, name='Book', location='Bedroom')

# HashString will be equal for base 16, base 64, or digest representations
assert(record.md5 == '9e107d9d372bb6826bd81d3542a419d6')
assert(record.md5 == 'nhB9nTcrtoJr2B01QqQZ1g==')
assert(record.md5 == md5_digest)

# Store hashes from base 16 strings
Evidence(md5='9e107d9d372bb6826bd81d3542a419d6', sha256='d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592', name='Book', location='Bedroom')
# Store hashes from base 64 strings
Evidence(md5='nhB9nTcrtoJr2B01QqQZ1g==', sha256='16j7swfXgJRpypq8sAguT41WUeRtPNt2LQLQvzfJ5ZI=', name='Book', location='Bedroom')
```

#### Class
*   **HashField(bit_length=None, max_length=None)**  
    Neither argument is required, but at least one must be.
    *   **bit_length**: Raw bit length of the hash.  
        If not provided, the maximum _bit_length_ will be determined that can fit inside the _max_length_.  
        ie, md5 is 128 bits, sha256 is 256 bits.
    *   **max_length**: Analogous to _max_length_ on _Charfield_.  
        Field size in bytes. This will default to be the size that will contain the base64 representation of the _bit_length_, but can be set to be larger to accommodate legacy data or longer atypical hashes.


## OrderByField
[OrderByField][] is a database constraint enforced field providing similar functionality to the Django _Options.order_with_respect_to_ model option, which uses database expressions for incrementing instead of multiple queries.

It does not apply a Django _Options.order_by_ to the model like _Options.order_with_respect_to_ does, so query sets will not be ordered by this by default. Thus this field can be used to provide an ordering that does not affect queries and will not generate an _ORDER BY_ clause, but can be used for other purposes such as display.  
As this is a concrete field, a _Options.order_by_ can be specified on the model to add this behaviour. ie, `order_by = ('wrt_field_1', 'wrt_field_2', 'order_by_field')`

If _unique_for_fields_ is not specified it will instead default to being a _unique_ field, acting as an ordering for the entire model.

If _unique_for_fields_ is specified it will act similar to an _Options.order_with_respect_to_ on those fields.

The default value for the field will be one greater than the existing maximum value matching the ordering set.  
Using `Count` can lead to duplicate values if records are deleted unless all records are renumbered to maintain contiguous numbering. To avoid necessitating this and allow this field to be filled on the database side, it's done via a `SubQuery` with `Max`, so record creation is a single database query and can be done in bulk.

```python
# Order can be auto-set on save, or set manually
stick = Evidence(name='Sharp stick', location='Garden', order=10)
rock = Evidence(name='Rock', location='Garden')

assert(rock.order == None)
stick.save()
rock.save()
# Refresh with saved values, rock will come after stick
rock.refresh_from_db()
assert(rock.order == 11)
```

_*NOTE*: OrderByField requires django_types when using makemigrations, but this is not necessary for using the field. ie, In production settings._

#### Class
*   **OrderByField(unique_for_fields=None, db_constraint=True)**
    *   **unique_for_fields**: List of string field names that should be used similar to _Options.order_with_respect_to_.  
        All fields must be concrete as a _Options.unique_together_ model option (for these fields and self) is generated to create the appropriate database constraint.
    *   **db_constraint**: Whether this field will generate a database uniqueness constraint.  
        This is done via the same mechanism as _Options.unique_together_ if _unique_for_fields_, or through _Field.unique_ if not.

#### Model extras
These methods are added to the model the field is declared in, and behave in the same way as those provided by Django [Options.order_with_respect_to][].
*   **model.get_next_in_order()**  
    Same behaviour as _Options.order_with_respect_to_.
*   **model.get_previous_in_order()**  
    Same behaviour as _Options.order_with_respect_to_.
*   **model.get_FIELD_set()**  
    Same behaviour as _Options.order_with_respect_to_.
*   **model.set_FIELD_set(id_list, reset_values=False)**  
    Same behaviour as _Options.order_with_respect_to_ with the addition of _reset_values_.
    *   **id_list**: List of primary keys (or a queryset) that will be moved to the end of their ordering set in order.  
        Has the effect of reordering all listed to match order specified.  
    *   **reset_values**: Boolean to indicate whether to freshly renumber entire group from 0.  
        Must be updating entire group to reset_values

#### Reverse model extras
These methods are added models linked to within the ordering fields. ie, any in _unique_for_fields_.  
These can be used the same way as those provided by Django _Options.order_with_respect_to_.  
*   **model.get_MODEL_set(limit_to=None)**  
    Same behaviour as _Options.order_with_respect_to_ with the addition of _limit_to_.
    *   **limit_to**: An instance of the target/ordered model that can be used to restrict the set to a single grouping.  
        When using groupings that contain more than one foreign key coming from any single remote field will only cover one of those keys. The results will be grouped according to the _unique_for_fields_ order.  
        By specifying an instance from the grouped model, the results can be restricted to only the grouping that instance is in.
*   **model.set_MODEL_set(id_list, reset_values=False)**  
    Same behaviour as _model.set_FIELD_set()_.


## PartialIndex
[PartialIndex][] is an `Index` implementation allowing for partial indexes to be defined based upon Django filter or Q notation. Used within the _Options.indexes_ option on a model.

It behaves in the same way as [Django field lookups][], taking keyword arguments and `Q` objects as parameters to generate the clauses for the database index.  
There's no equivalent of `QuerySet.exclude()` and other filtering functions, but most of these can be achieved with [Django Q lookups][], such as `~Q()` notation to exclude.

#### Class
*   **PartialIndex(\*args, fields=[], name=None, \*\*kwargs)**  
    Very similar behaviour to `Index` and `QuerySet`.
    *   **args**: `Q` objects to restrict the index generated, same as for `QuerySet.filter()`.
    *   **fields**: List of fields to include in the index.
    *   **name**: Name to use when creating the index on the database.  
        If not provided, something will be generated for it.
    *   **kwargs**: Keyword filters to restrict the index generated, same as for `QuerySet.filter()`


# Utility Classes
Various classes used by the exposed fields and functions to abstract or encapsulate necessary functionality.


## HashString
[HashString][] is an `str` subclass with additional hashing based methods and an `__eq__()` method that will attempt to coerce comparisons to hashes to the same representation. ie, allowing base64 and base16 representations of the same hash to evaluate as equal.

String representation is lowercase base16, which is the most human-friendly, while the `__repr__()` will be base64.

Bytes representation is the base256 (raw) bytes of the hash itself, and not bytes reflecting any specific representation.

The `__hash__()` of all instances is based upon the base64 representation, so two instances generated from different representations of the same hash will hash to the same, such that `set` or `dict` operations will behave in an intuitive manner.

#### Class methods
*   **HashString.from_b16(value)**  
    *   **value**: Base16 string used to create a new instance.
*   **HashString.from_b64(value)**  
    *   **value**: Base64 string used to create a new instance.
*   **HashString.from_b256(value)**  
    *   **value**: Bytes or digest of a hash used to create a new instance.


## UniqueForFieldsMixin
[UniqueForFieldsMixin][] with added to a field gives it an additional _unique_for_fields_ argument.

When _unique_for_fields_ is provided, an additional database constraint is added via _Options.unique_together_ for this field and all fields specified.

As a _Options.unique_together_ completely covers the utility of the _unique_ field option, if _unique_for_fields_ is provided, it will remove _unique_ if set on the field.


## BypassExpression
[BypassExpression][] wraps an `Expression` in the same way as `ExpressionWrapper` but prevents validation from flagging the expression as containing column references or aggregates.

Most useful to allow some expressions to be used in _INSERT_ statements that are otherwise rejected by Django for being too difficult to validate.  
Without Django validating any references or aggregates within the expression, there are no warnings about these if they are invalid or cannot be resolved.

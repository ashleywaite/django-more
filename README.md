# django-more

A collection of Django patches and extensions to give more of the features and functionality that I want or expect from Django.  
_Currently aimed only at Django 1.11_


## django_more
[django_more](django_more/) contains field and classes for Django that do not require any patching and can be used directly.

*   **django_more.storages**  
    Allows defining Django storages in _settings_ and generating the storage classes as needed in _django_more.storages.NAME_.
*   **django_more.PartialIndex**  
    Database partial indexes using Django query and `Q()` notation.  
    Working on postgres, untested elsewhere.
*   **django_more.HashField**  
    Field for storing hashes and removing the issues with comparing, generating, and converting hashes.
*   **django_more.OrderByField**  _(requires django_types)_  
    Field for _order_with_respect_to_ similar functionality, with support for an arbitrary number of fields in the ordering, database constraints, bulk updates, single query creation, and generic keys.

_Placing django_more into Django INSTALLED_APPS will automatically invoke django_types.patch_types() - only necessary for OrderByField makemigrations_


## django_enum
[django_enum](django_enum/) patches Django to add EnumFields, with enum state information in migrations to allow for consistent migrations compatible with postgres and mysql.

*   **django_enum.EnumField**  _(requires django_types)_  
    Django field based upon python 3.4 (PEP435) `Enum` with support for database enum fields.
*   **django_enum.enum_meta**  
    Decorator to hide _Meta_ classes in standard python `Enum`.
*   **django_enum.patch_enum()**  
    Applies patches to Django necessary for this module to work.

_Placing django_enum into Django INSTALLED_APPS will automatically invoke patch_enum() and django_types.patch_types()_


## django_types
[django_types](django_types/) patches Django to add support for custom database types to be used within migrations.  
Not intended to be used directly, but by other reusable apps adding fields that rely on the additional functionality.

*   **django_types.CustomTypeField**  
    Base implementation for custom types that can be managed within the migration framework.
*   **django_types.patch_types()**  
    Applies patches to Django necessary for this module to work.

_Apps dependent on this should check for ProjectState.add_type() support, and if not present apply this with patch_types()_


## django_cte
[django_cte](django_cte/) patches Django to add CTE based functionality.

*   **django_cte.patch_cte()**  
    Applies patches to Django necessary for this module to work.

**Not included in distributions until out of WIP state**  
_Placing django_cte into Django INSTALLED_APPS will automatically invoke patch_cte()_


## patchy
[patchy](patchy/) is class based monkey patching package used by the other _django-more_ modules to apply their patches in a consistent and safe manner that is hopefully less fragile to Django core changes.

*   **patchy.patchy()**  
    Creates a class and context manager to apply patches.
*   **patchy.super_patchy()**  
    Provides functionality similar to `super()` to functions and methods that have been patched in, allowing calls the methods they replaced.

-----

-----

-----

## Version History

**0.2.2**
*   Added: Arbitrary field dependencies via _django_types_.
*   Bugfix: `OrderByField` uses dependencies to prevent field creation order issues.

**0.2.1**
*   Added: `OrderByField` now matches all _order_with_respect_to_ functionality.
*   Documentation: _django_more_ module, substantial rewrite and expansion of [README](django_more/README.md).
*   Documentation: _django-more_ base [README](readme.md) substantially cleaned up.
*   Bugfixes: Migrations interacting badly with OrderByField and defaults.

**0.2.0**  
*   Added: `django_more.OrderByField`.
*   Bugfix: A bad reference caused `EnumField` to break on cascade.
*   Bugfix: Defaults to `EnumField` are stringified so that migrations don't break if Enums are relocated.
*   Refactored: _django_more.fields_ into sub-module.
*   Documentation: _django_more_ module, added [README](django_more/README.md).  

**0.1.1**  
*   Bugfix: Include _django_types_ in distribution as necessary for _django_enum_.

**0.1.0**  
*   Initial release without _django_cte_ module.  
*   Added: `django_enum.EnumField`.
*   Added: `django_more.PartialIndex`.
*   Added: `django_more.HashField`.
*   Added: `django_more.storages`.
*   Documentation: _django_enum_ module, added [README](django_enum/README.md).
*   Documentation: _django_types_ module, added [README](django_types/README.md).
*   Documentation: _patchy_ module, added [README](patchy/README.md).

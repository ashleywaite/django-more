# django-more

A collection of Django patches and extensions to give more of the features and functionality that I want or expect from Django.  
_Currently aimed only at Django 1.11_


## django_more

Extras for Django that do not require any patching and can be used directly.
 * *django_more.storages*
 * *django_more.PartialIndex*
 * *django_more.HashField*


## django_cte

Patches Django to add CTE based functionality.
* django_cte.patch_cte()

_Placing django_cte into Django INSTALLED_APPS will automatically invoke patch_cte()_


## django_enum

Patches Django to add EnumFields, with enum state information in migrations to allow for consistent migrations compatible with postgres and mysql.
 * django_enum.EnumField
 * django_enum.enum_meta
 * django_enum.patch_enum()

_Placing django_enum into Django INSTALLED_APPS will automatically invoke patch_enum()_


## django_types

Patches Django to add support for custom database types to be used within migrations.
 * django_types.patch_types()

_To avoid additional dependencies in INSTALLED_APPS, apps adding types requiring this should check for ProjectState.add_type() support, and if not present apply this with patch_types()_


## patchy

A class based monkey patching package used by the other django_more packages to apply their patches in a consistent and safe manner that is hopefully less fragile to Django core changes.
* patchy.patchy()
* patchy.super_patchy()

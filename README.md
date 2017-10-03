# django-more

A collection of django patches and extensions to give more of the features and
 functionality that I want or expect from Django.  
_Currently aimed only at Django 1.11_


## django_more

Extras for Django that do not require any patching and can be used directly.
 * *django_more.storages*
 * *django_more.PartialIndex*
 * *django_more.HashField*


## django_cte

Patches Django to add CTE based functionality.

_Placing django_cte into Django INSTALLED_APPS is all that's required to patch_


## django_enum

Patches Django to add EnumFields, with enum state information in migrations
 to allow for consistent migrations compatible with postgres and mysql.

 * django_enum.EnumField

_Placing django_enum into Django INSTALLED_APPS is all that's required to patch_


## patchy

A class based monkey patching package used by the other django_more packages to
 apply their patches in a consistent and safe manner that is hopefully less fragile
 to Django core changes.

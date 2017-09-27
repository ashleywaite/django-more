# django-more

A collection of django patches and extensions to give more of the features and
 functionality that I want or expect from Django.  
_Currently aimed only at Django 1.11_


## django-more

Extras for Django that do not require any patching and can be used directly.
 * *django-more.storages* 
 * *django-more.PartialIndex*
 * *django-more.HashField*


## django-cte

Patches Django to add CTE based functionality.
 * django-cte.patch_cte()


## django-enum

Patches Django to add EnumFields, with enum state information in migrations
 to allow for consistent migrations compatible with postgres.
 * django-enum.patch_enum()


## patchy

A class based monkey patching package used by the other django-more packages to
 apply their patches in a consistent and safe manner that is hopefully less fragile
 to Django core changes.

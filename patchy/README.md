# patchy

Generic monkey patching tool to keep patches better organised and uniform.


## Using patchy

**patchy(target, source=None)**  
Takes a target (class or module to be patched) and source (class or module to pull patches from) and returns an instance that allows you to apply patches.  
Source or target can be a class or module instance, or a dotted path to one.
If source is not provided, then _auto()_ and _apply(attrs)_ will not be able to source items to patch and will require them provided directly.

```python
from patchy import patchy

with patchy('django', 'my_djago_patch') as p:
    p.add('something_new', named=my_func)
    p.cls('db', 'my_db_patch').auto()
```    

**super_patchy(\*args, do_call=True, \*\*kwargs)**  
When called from within a function that has been monkey patched into somewhere else by patchy, will call or return the function that it replaced. If called from a function that appears to be bound (first argument is _self_ or _cls_) will also bind that value to the replaced function, so these never need to be provided.
When called with _do_call=False_ will return the function itself.
When called without _do_call_ then will call the replaced function passing _\*args_ and _\*\*kwargs_ and return the return value from it.

```python
from patchy import super_patchy

def new_func(arg):
    super_patchy(arg)
    old_func = super_patchy(do_call=False)
```


## Patchy instances

**add(\*attrs, \*\*kattrs)**  
_apply()_ without merge.

**merge(\*attrs, \*\*kattrs)**  
_apply()_ with merge.

**auto(merge=True, types=object)**  
Apply non-private (startswith('\_')) locally declared objects (hasattr('\_\_module__')) such as functions and classes) of the source to the target. Also applies any attribute (regardless of type) in the _instance.allow_ set.
_(class patching)_ Also apply all primative attributes. Default _allow_ includes {'\_\_init__', '\_\_new__'}
_(module patching)_ Default _allow_ includes {'\_\_all__'}

**apply(attrs, kattrs, merge=False)**  
Any attrs with a *\_\_name__* attribute will be applied to the target with that as their attribute name.  
Any values provided as attrs will be fetched from the provided source and applied to the target.  
Any values provided as kattrs will be applied directly to the target with the name specified.  
Merge will attempt to combine collections instead of replacing them.

**cls(target, source=None)** (modules only)  
Get a patchy instance for the specified class, relative to the module being patched.  
If source is not specified it will attempt to be derived from the source of this instance.
For example, from patchy('django', 'django_patch').cls('db.models.Model'):
 * Look for class within a containing module via full name relative to this instance substituting module_sep (default '\_')  
 ie, 'Model' within 'django_db_models' relative to 'django_patch'
 * Look for class within the source module for this instance.  
 ie, 'Model' within 'django_patch'

**mod(target, source=None)** (module only)  
Get a patchy instance for the specified module, relative to the module being patched.  
If source is not specified it will attempt to be derived from the source of this instance.  
For example, from patchy('django', 'django_patch').mod('db.models'):
 * Look for module via short name relative to this instance.  
 ie, 'db.models' relative to 'django_patch'
 * Look for module via full name relative to this instance substituting module_sep (default '\_')  
 ie, 'django_db_models' relative to 'django_patch'


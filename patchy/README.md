# patchy

Generic monkey patching tool to keep patches better organised and uniform.


## patchy()

Takes a target (class or module to be patched) and source (class or module to use for named attributes to patch in) and returns an instance that allows you to apply patches to it.  
Source or target can be a class or module instance, or a dotted path to one.

```python
from patchy import patchy

with patchy('django', 'my_djago_patch') as p:
    p.add('something_new', named=my_func)
    p.cls('db', 'my_db_patch').auto()
```    


## super_patchy()

When called from within a function that has been monkey patched into somewhere else by patchy, will call or return the function that it replaced.

```python
from patchy import super_patchy

def new_func(arg):
    super_patchy(arg)
    old_func = super_patchy(do_call=False)
```


## Patch class

**add(\*attrs, \*\*kattrs)**  
_apply()_ without merge.

**merge(\*attrs, \*\*kattrs)**  
_apply()_ with merge.

**auto(merge=True, types=object)**  
Will automatically apply all non-private attributes of the source to the target.  
_types_ will filter the attributes automatically applied to those that are instances provided, as per _isinstance()_

**apply(attrs, kattrs, merge=False)**  
Any attrs with a *\_\_name__* attribute will be applied to the target with that as their attribute name.  
Any values provided as attrs will be fetched from the provided source and applied to the target.  
Any values provided as kattrs will be applied directly to the target with the name specified.  
Merge will attempt to combine collections instead of replacing them.

**cls(target, source=None)**  
Get a patching instance for the specified class, relative to the patching class it is called from.

**mod(target, source=None)**  
Get a patching instance for the specified module, relative to the patching class it is called from.

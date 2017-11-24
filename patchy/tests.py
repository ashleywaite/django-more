import sys
from importlib import import_module
from types import MethodType
from unittest import TestCase

from . import patchy
from . import testmod


class TestPatchy(TestCase):
    def setUp(self):
        global testmod
        # As tests alter classes directly, need to explcitly remove module sys cache
        if testmod.__name__ in sys.modules:
            del sys.modules[testmod.__name__]
        # Reload module freshly and update module reference
        testmod = import_module(testmod.__name__)

    def test_method_before_instances(self):
        """ Patching before any use of class """
        with patchy(testmod.Original, testmod.SimpleThings) as p:
            p.add('get_string')
        k = testmod.Original()
        self.assertEqual(k.get_string(), testmod.STR_REP)

    def test_method_after_instances(self):
        """ Patching after class is in use """
        k = testmod.Original()
        self.assertEqual(k.get_string(), testmod.STR_ORI)
        with patchy(testmod.Original, testmod.SimpleThings) as p:
            p.add('get_string')
        self.assertEqual(k.get_string(), testmod.STR_REP)

    def test_class_reference_stable(self):
        """ Take reference to class before patching """
        Original = testmod.Original
        with patchy(testmod.Original, testmod.SimpleThings) as p:
            p.add('get_string')
        k = testmod.Original()
        self.assertEqual(k.__class__, Original)

    def test_method_uses_original(self):
        """ Patching but still using the original function """
        k = testmod.Original()
        self.assertEqual(k.get_strings(), [testmod.STR_ORI])
        self.assertEqual(k.get_strings('test'), [testmod.STR_ORI, 'test'])
        with patchy(testmod.Original, testmod.SuperPatchyThings) as p:
            p.add('get_strings')
        self.assertEqual(k.get_strings(), [testmod.STR_ADD, testmod.STR_ORI])
        self.assertEqual(k.get_strings('test'), [testmod.STR_ADD, testmod.STR_ORI, 'test'])

    def test_method_uses_super(self):
        """ Patching but still using the original function """
        k = testmod.Original()
        self.assertEqual(k.get_strings(), [testmod.STR_ORI])
        self.assertEqual(k.get_strings('test'), [testmod.STR_ORI, 'test'])
        with patchy(testmod.Original, testmod.SuperThings) as p:
            p.add('get_strings')
        self.assertEqual(k.get_strings(), [testmod.STR_ADD, testmod.STR_ORI])
        self.assertEqual(k.get_strings('test'), [testmod.STR_ADD, testmod.STR_ORI])

    def test_method_with_instance_override(self):
        """ Patching but an instance has an override of the method that shouldn't be removed """
        k = testmod.Original()
        k.get_string = MethodType(lambda self: testmod.STR_OVR, k)
        self.assertEqual(k.get_string(), testmod.STR_OVR)
        with patchy(testmod.Original, testmod.SimpleThings) as p:
            p.add('get_string')
        self.assertEqual(k.get_string(), testmod.STR_OVR)

    def test_method_with_instance_override_containing_super(self):
        """ Patching but an instance has an override of the method that calls super() """
        k = testmod.Original()
        k.get_string = MethodType(lambda self: super(self.__class__, self).get_string() + testmod.STR_OVR, k)
        self.assertEqual(k.get_string(), testmod.STR_INH + testmod.STR_OVR)
        with patchy(testmod.Original, testmod.SimpleThings) as p:
            p.add('get_string')
        self.assertEqual(k.get_string(), testmod.STR_INH + testmod.STR_OVR)

    def test_class_method(self):
        """ Patching a class method """
        k = testmod.Original()
        self.assertEqual(k.get_class_strings(), [testmod.STR_ORI, testmod.Original.__name__])
        self.assertEqual(k.get_class_strings('test'), [testmod.STR_ORI, testmod.Original.__name__, 'test'])
        with patchy(testmod.Original, testmod.SimpleThings) as p:
            p.add('get_class_strings')
        self.assertEqual(k.get_class_strings(), [testmod.STR_REP, testmod.Original.__name__])
        self.assertEqual(k.get_class_strings('test'), [testmod.STR_REP, testmod.Original.__name__, 'test'])

    def test_static_method(self):
        """ Patching a static method """
        k = testmod.Original()
        self.assertEqual(k.get_static_strings(), [testmod.STR_ORI])
        self.assertEqual(k.get_static_strings('test'), [testmod.STR_ORI, 'test'])
        with patchy(testmod.Original, testmod.SimpleThings) as p:
            p.add('get_static_strings')
        self.assertEqual(k.get_static_strings(), [testmod.STR_REP])
        self.assertEqual(k.get_static_strings('test'), [testmod.STR_REP, 'test'])

    def test_inherited_method(self):
        """ Patching a method that is inherited from ancestor """
        k = testmod.Original()
        self.assertEqual(k.get_inherited_string(), testmod.STR_INH)
        with patchy(testmod.Original, testmod.SimpleThings) as p:
            p.add('get_inherited_string')
        self.assertEqual(k.get_inherited_string(), testmod.STR_REP)

    def test_inherited_class_method(self):
        """ Patching a class method that is inherited from ancestor  """
        k = testmod.Original()
        self.assertEqual(k.get_inherited_class_strings(), [testmod.STR_INH, testmod.Original.__name__])
        self.assertEqual(k.get_inherited_class_strings('test'), [testmod.STR_INH, testmod.Original.__name__, 'test'])
        with patchy(testmod.Original, testmod.SimpleThings) as p:
            p.add('get_inherited_class_strings')
        self.assertEqual(k.get_inherited_class_strings(), [testmod.STR_REP, testmod.Original.__name__])
        self.assertEqual(k.get_inherited_class_strings('test'), [testmod.STR_REP, testmod.Original.__name__, 'test'])

    def test_inherited_static_method(self):
        """ Patching a static method that is inherited from ancestor """
        k = testmod.Original()
        self.assertEqual(k.get_inherited_static_strings(), [testmod.STR_INH])
        self.assertEqual(k.get_inherited_static_strings('test'), [testmod.STR_INH, 'test'])
        with patchy(testmod.Original, testmod.SimpleThings) as p:
            p.add('get_inherited_static_strings')
        self.assertEqual(k.get_inherited_static_strings(), [testmod.STR_REP])
        self.assertEqual(k.get_inherited_static_strings('test'), [testmod.STR_REP, 'test'])

    def test_property(self):
        """ Patching a property/descriptor """
        k = testmod.Original()
        self.assertEqual(k.get_string(), testmod.STR_ORI)
        self.assertEqual(k.string, testmod.STR_ORI)
        with patchy(testmod.Original, testmod.SimpleThings) as p:
            p.add('string')
        self.assertEqual(k.get_string(), testmod.STR_REP)
        self.assertEqual(k.string, testmod.STR_REP)

    def test_method_in_class_with_slots(self):
        """ Patching a method that exists on a class with slots """
        k = testmod.OriginalSlots()
        self.assertRaises(AttributeError, k.get_string)
        k._string = testmod.STR_OVR
        self.assertEqual(k.get_string(), testmod.STR_OVR)
        self.assertEqual(k.get_slots_strings('test'), [testmod.STR_OVR, 'test'])
        with patchy(testmod.OriginalSlots, testmod.SimpleThings) as p:
            p.add('get_slots_strings')
        self.assertEqual(k.get_slots_strings(), [testmod.STR_REP])
        self.assertEqual(k.get_slots_strings('test'), [testmod.STR_REP, 'test'])

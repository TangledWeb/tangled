import unittest
from doctest import DocTestSuite

import tangled.decorators
from tangled.decorators import cached_property


def load_tests(loader, tests, ignore):
    tests.addTests(DocTestSuite(tangled.decorators))
    return tests


class Class:

    @cached_property
    def cached(self):
        return 'cached'


class TestCachedProperty(unittest.TestCase):

    def test_get(self):
        obj = Class()
        self.assertEqual(obj.cached, 'cached')

    def test_set(self):
        obj = Class()
        obj.cached = 'saved'
        self.assertEqual(obj.cached, 'saved')

    def test_get_set(self):
        obj = Class()
        self.assertEqual(obj.cached, 'cached')
        obj.cached = 'saved'
        self.assertEqual(obj.cached, 'saved')

    def test_del(self):
        obj = Class()
        self.assertEqual(obj.cached, 'cached')
        del obj.cached
        self.assertEqual(obj.cached, 'cached')
        obj.cached = 'saved'
        self.assertEqual(obj.cached, 'saved')
        del obj.cached
        self.assertEqual(obj.cached, 'cached')
        del obj.cached


class ClassWithDependentProperties(Class):

    def __init__(self):
        self.regular = 1
        super().__init__()

    @cached_property('cached')
    def dependent(self):
        return self.cached + '.xxx'

    @cached_property('regular')
    def dependent_on_regular(self):
        return self.regular

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        cached_property.reset_dependents_of(self, name)

    def __delattr__(self, name):
        super().__delattr__(name)
        cached_property.reset_dependents_of(self, name)


class TestCachedPropertyWithDependencies(unittest.TestCase):

    def test_get(self):
        obj = ClassWithDependentProperties()
        self.assertEqual(obj.cached, 'cached')
        self.assertEqual(obj.dependent, 'cached.xxx')

    def test_set(self):
        obj = ClassWithDependentProperties()
        self.assertEqual(obj.cached, 'cached')
        # self.assertEqual(obj.dependent, 'cached.xxx')
        # obj.dependent = 'XXX'
        # self.assertEqual(obj.cached, 'cached')
        # self.assertEqual(obj.dependent, 'XXX')

    def test_del(self):
        obj = ClassWithDependentProperties()
        del obj.dependent
        self.assertEqual(obj.cached, 'cached')
        self.assertEqual(obj.dependent, 'cached.xxx')
        del obj.dependent
        self.assertEqual(obj.cached, 'cached')
        self.assertEqual(obj.dependent, 'cached.xxx')

    def test_set_dependency(self):
        obj = ClassWithDependentProperties()
        self.assertEqual(obj.cached, 'cached')
        self.assertEqual(obj.dependent, 'cached.xxx')
        obj.cached = 'new'
        self.assertEqual(obj.cached, 'new')
        self.assertEqual(obj.dependent, 'new.xxx')

    def test_del_dependency(self):
        obj = ClassWithDependentProperties()
        self.assertEqual(obj.cached, 'cached')
        self.assertEqual(obj.dependent, 'cached.xxx')
        del obj.cached
        self.assertEqual(obj.cached, 'cached')
        self.assertEqual(obj.dependent, 'cached.xxx')

    def test_get_set(self):
        obj = ClassWithDependentProperties()
        self.assertEqual(obj.dependent, 'cached.xxx')
        obj.dependent = 'XXX'
        self.assertEqual(obj.dependent, 'XXX')

    def test_set_directly_then_del_dependency(self):
        obj = ClassWithDependentProperties()
        self.assertEqual(obj.dependent, 'cached.xxx')
        obj.dependent = 'XXX'
        self.assertEqual(obj.dependent, 'XXX')
        del obj.cached
        # obj.dependent was set directly, so it's not reset when
        # obj.cached is deleted.
        self.assertEqual(obj.dependent, 'XXX')
        # Resetting obj.dependent will cause it to be recomputed.
        del obj.dependent
        obj.cached = 'new'
        self.assertEqual(obj.dependent, 'new.xxx')

    def test_set_regular_attr(self):
        obj = ClassWithDependentProperties()
        self.assertEqual(obj.dependent_on_regular, 1)
        obj.regular = 2
        self.assertEqual(obj.dependent_on_regular, 2)

    def test_del_regular_attr(self):
        obj = ClassWithDependentProperties()
        self.assertEqual(obj.dependent_on_regular, 1)
        del obj.regular
        self.assertRaises(AttributeError, lambda: obj.dependent_on_regular)
        obj.regular = 2
        self.assertEqual(obj.dependent_on_regular, 2)

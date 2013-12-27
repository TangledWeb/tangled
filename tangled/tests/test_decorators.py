import unittest

from tangled.decorators import reify, cached_property


class Class:

    @cached_property
    def cached(self):
        return 'cached'

    @reify
    def reified(self):
        return 'reified'


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
        del obj.cached  # del'ing a property that hasn't been set is a no-op
        obj.cached = 'saved'
        self.assertEqual(obj.cached, 'saved')
        del obj.cached


class TestReify(unittest.TestCase):

    def test_get(self):
        obj = Class()
        self.assertEqual(obj.reified, 'reified')

    def test_set(self):
        obj = Class()
        obj.reified = 'concrete'
        self.assertEqual(obj.reified, 'concrete')

    def test_get_set(self):
        obj = Class()
        self.assertEqual(obj.reified, 'reified')
        obj.reified = 'concrete'
        self.assertEqual(obj.reified, 'concrete')

    def test_del(self):
        obj = Class()
        with self.assertRaises(AttributeError):
            del obj.reified
        obj.reified = 'concrete'
        self.assertEqual(obj.reified, 'concrete')
        del obj.reified

import unittest

from tangled.decorators import cached_property


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
        with self.assertRaises(AttributeError):
            del obj.cached
        self.assertEqual(obj.cached, 'cached')
        del obj.cached
        self.assertEqual(obj.cached, 'cached')
        obj.cached = 'saved'
        self.assertEqual(obj.cached, 'saved')
        del obj.cached
        self.assertEqual(obj.cached, 'cached')
        del obj.cached
        with self.assertRaises(AttributeError):
            del obj.cached

import unittest


from tangled.registry import Registry


class TestRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = Registry()

    def test_register(self):
        self.registry.register(object, None)

    def test_get(self):
        self.registry.register(object, 1)
        self.registry.get(object) == 1

    def test_get_default(self):
        component = object()
        self.registry.register(object, component)
        self.assertIs(self.registry.get(object), component)
        self.assertIsNone(self.registry.get(object, 'differentiator'))
        self.assertIsNone(self.registry.get('not registered'))
        self.assertEqual(self.registry.get('not registered', default={}), {})

    def test_get_item(self):
        with self.assertRaises(KeyError):
            self.registry[object]

        component = object()
        self.registry.register(object, component)
        self.assertIs(self.registry[object], component)

        component = object()
        self.registry.register(object, component, 2)
        self.assertIs(self.registry[[object, 2]], component)

    def test_set_item(self):
        component = object()
        self.registry[object] = component
        self.assertTrue(self.registry.contains(object))
        self.registry[[object, 'differentiator']] = component
        self.assertTrue(self.registry.contains(object, 'differentiator'))

    def test_contains(self):
        self.registry.register(object, None)
        self.assertTrue(self.registry.contains(object, None))
        self.assertIn([object, None], self.registry)

    def test_does_not_contain(self):
        self.registry.register(object, None)
        self.assertFalse(self.registry.contains(object, 1))
        self.assertNotIn([object, 1], self.registry)

    def test_get_all(self):
        component1 = object()
        component2 = object()
        self.registry.register(object, component1, 1)
        self.registry.register(object, component2, 2)
        components = self.registry.get_all(object)
        self.assertEqual(len(components), 2)
        self.assertIs(components[0], component1)
        self.assertIs(components[1], component2)

    def test_get_all_default(self):
        self.assertIsNone(self.registry.get_all(object))
        default = object()
        self.assertIs(self.registry.get_all(object, default), default)

    def test_get_all_as_dict(self):
        self.registry.register(object, object(), 1)
        self.registry.register(object, object(), 2)
        components = self.registry.get_all(object, as_dict=True)
        self.assertIsInstance(components, dict)
        self.assertIn(1, components)
        self.assertIn(2, components)

    def test_has_any(self):
        self.assertFalse(self.registry.has_any(object))
        self.registry.register(object, object(), 1)
        self.registry.register(object, object(), 2)
        self.assertTrue(self.registry.has_any(object))

    def test_remove(self):
        with self.assertRaises(KeyError):
            self.registry.remove(object)
        self.registry.register(object, object(), 1)
        self.registry.register(object, object(), 2)
        self.registry.remove(object, 1)
        self.assertNotIn([object, 1], self.registry)
        self.assertIn([object, 2], self.registry)

import os
import sys
import unittest

from tangled import util


class Test_load_object(unittest.TestCase):

    def test_load_object(self):
        obj = util.load_object('tangled.util:load_object')
        self.assertIs(obj, util.load_object)

    def test_load_object_pass_name(self):
        obj = util.load_object('tangled.util', 'load_object')
        self.assertIs(obj, util.load_object)

    def test_load_object_with_dotted_name(self):
        obj = util.load_object('sys:implementation.name')
        self.assertEqual(obj, sys.implementation.name)

    def test_load_module(self):
        module = util.load_object('tangled.util')
        self.assertIs(module, util)


class Test_asset_path(unittest.TestCase):

    def test_asset_path(self):
        path = util.asset_path('tangled.util:dir/file')
        self.assertTrue(path.endswith('/tangled/tangled/util/dir/file'))

    def test_asset_path_with_rel_path(self):
        path = util.asset_path('tangled.util', 'dir/file')
        self.assertTrue(path.endswith('/tangled/tangled/util/dir/file'))

    def test_asset_path_with_base_rel_path(self):
        path = util.asset_path('tangled.util:dir', 'file')
        self.assertTrue(path.endswith('/tangled/tangled/util/dir/file'))

    def test_asset_path_for_package(self):
        path = util.asset_path('tangled.util')
        self.assertTrue(path.endswith('/tangled/tangled/util'))

    def test_asset_path_for_module(self):
        path = util.asset_path('tangled.util')
        self.assertTrue(path.endswith('/tangled/tangled/util'))

    def test_asset_path_for_namespace_pacakge_raises_ValueError(self):
        self.assertRaises(ValueError, util.asset_path, 'tangled')


class Test_abs_path(unittest.TestCase):

    def test_abs_path_for_rel_path(self):
        cwd = os.path.dirname(os.getcwd())
        path = util.abs_path('..')
        self.assertTrue(os.path.isabs(path))
        self.assertEqual(path, cwd)

    def test_abs_path_for_abs_path(self):
        path = util.abs_path('/x/y/z')
        self.assertEqual(path, '/x/y/z')

    def test_abs_path_for_asset(self):
        path = util.abs_path('tangled.util:x/y')
        self.assertTrue(os.path.isabs(path))
        expected = os.path.join(os.path.dirname(util.__file__), 'x/y')
        self.assertTrue(path.endswith('/tangled/tangled/util/x/y'))
        self.assertEqual(path, expected)


class Test_get_items_with_key_prefix(unittest.TestCase):

    def test_get_items_with_key_prefix(self):
        items = {
            'a.a': 1, 'a.b': 2,
            'b.a': 1, 'b.b': 2,
        }
        items_with_prefix = util.get_items_with_key_prefix(items, 'a.')
        expected = {'a': 1, 'b': 2}
        self.assertEqual(items_with_prefix, expected)

    def test_get_items_with_key_prefix_from_sequence(self):
        items = [
            ('a.a', 1), ('a.b', 2),
            ('b.a', 1), ('b.b', 2),
        ]
        items_with_prefix = util.get_items_with_key_prefix(items, 'a.')
        expected = [('a', 1), ('b', 2)]
        self.assertEqual(items_with_prefix, expected)

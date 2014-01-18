import unittest

from tangled import converters
from tangled import util


class Test_as_list_of_objects(unittest.TestCase):

    def test_empty_string(self):
        objects = converters.as_list_of_objects('')
        self.assertEqual(objects, [])

    def test_one_item_string(self):
        objects = converters.as_list_of_objects('tangled.converters')
        self.assertEqual(objects, [converters])

    def test_multi_item_string(self):
        objects = converters.as_list_of_objects(
            'tangled.converters tangled.util')
        self.assertEqual(objects, [converters, util])

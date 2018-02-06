import unittest


import tangled.settings
import tangled.util


class TestSettings(unittest.TestCase):

    def test_parse_settings(self):
        original_settings = {}
        settings = tangled.settings.parse_settings(original_settings)
        self.assertEqual(settings, {})
        self.assertIsNot(settings, original_settings)

    def test_parse_settings_with_defaults(self):
        settings = {
            'a': '1',
        }
        settings = tangled.settings.parse_settings(settings, defaults={'b': 2})
        self.assertEqual(settings, {'a': 1, 'b': 2})

    def test_parse_settings_with_prefix(self):
        settings = {
            'a.a': '1',
            'a.b': '2',
            'b.a': '3',
        }
        settings = tangled.settings.parse_settings(settings, prefix='a.')
        self.assertEqual(settings, {'a': 1, 'b': 2})

    def test_parse_settings_with_extras(self):
        settings = {
            'a': '1',
        }
        settings = tangled.settings.parse_settings(
            settings, defaults={'a': 'a', 'b': 'b'}, extra={'a': 'A'})
        self.assertEqual(settings, {'a': 'A', 'b': 'b'})

    def test_parse_settings_with_type(self):
        settings = {
            'a:str': '1',
        }
        settings = tangled.settings.parse_settings(settings)
        self.assertEqual(settings, {'a': '1'})

    def test_parse_settings_with_type_as_asset_path(self):
        settings = {
            'a:tangled.util:load_object': '"tangled.util:load_object"',
        }
        settings = tangled.settings.parse_settings(settings)
        self.assertEqual(settings, {'a': tangled.util.load_object})

import unittest


import tangled.settings


class TestSettings(unittest.TestCase):

    def test_parse_settings(self):
        original_settings = {}
        settings = tangled.settings.parse_settings(original_settings)
        self.assertEqual(settings, {})
        self.assertIsNot(settings, original_settings)

    def test_parse_settings_with_defaults(self):
        settings = {
            'a': 1,
        }
        settings = tangled.settings.parse_settings(settings, defaults={'b': 2})
        self.assertEqual(settings, {'a': 1, 'b': 2})

    def test_parse_settings_with_prefix(self):
        settings = {
            'a.a': 1,
            'a.b': 2,
            'b.a': 1,
        }
        settings = tangled.settings.parse_settings(settings, prefix='a.')
        self.assertEqual(settings, {'a': 1, 'b': 2})

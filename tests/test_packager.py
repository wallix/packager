#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from wallix_packager.packager import replace_dict_all, read_and_update_config, update_config_variables

class TestPackager(unittest.TestCase):
    def test_replace_dict_all(self):
        self.assertEqual(
            replace_dict_all(
                'a %A% aa %AA% %B% a %A%%D% aa %C% %B%',
                {
                    'A': 'AA',
                    'B': 'xY',
                    'C': 'A',
                    'AA': 'plop',
                }
            ),
            'a AA aa plop xY a AA%D% aa A xY')

    def test_read_and_update_config(self):
        config = read_and_update_config(
            'tests/data/config1', {'DIST_NAME':'debian', 'DIST_ID':'squeeze'})
        self.assertEqual(config, {
            'DIST_ID': 'squeeze',
            'DIST_NAME': 'debian',
            'PKG_DISTRIBUTION': 'squeeze',
            'X': '3',
            'VAR1': 'v1',
            'VAR2': 'v2',
            'VAR3': 'v3'
        })

    def test_update_config_variables(self):
        config = {'V':'x'}
        unparsed = update_config_variables(config, ['XYZ', 'X-Y', 'X=', 'ABC=123', 'V+=y'])
        self.assertEqual(config, {'V': 'xy', 'X': '', 'ABC': '123'})
        self.assertEqual(unparsed, ['XYZ', 'X-Y'])


if __name__ == '__main__':
    unittest.main()

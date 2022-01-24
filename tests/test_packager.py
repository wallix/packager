#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import os
import sys

dir_path = os.path.dirname(os.path.realpath(__file__))

sys.path.append(os.path.dirname(dir_path))
import packager

class TestPackager(unittest.TestCase):
    def test_replace_dict_all(self):
        self.assertEqual(
            packager.replace_dict_all(
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
        config = packager.read_and_update_config(
            f'{dir_path}/data/config1', {'DIST_NAME':'debian', 'DIST_ID':'squeeze'})
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
        unparsed = packager.update_config_variables(config, ['XYZ', 'X-Y', 'X=', 'ABC=123', 'V+=y'])
        self.assertEqual(config, {'V': 'xy', 'X': '', 'ABC': '123'})
        self.assertEqual(unparsed, ['XYZ', 'X-Y'])

    def test_less_version(self):
        self.assertEqual(packager.less_version('1.0.0.0', '1.0.0.0'), False)
        self.assertEqual(packager.less_version('0.0.9.0', '1.0.0.0'), True)
        self.assertEqual(packager.less_version('1.0.0.0', '1.0.0.1'), True)
        self.assertEqual(packager.less_version('1.0.0.1', '1.0.0.1'), False)
        self.assertEqual(packager.less_version('1.0.0.1', '2.0.0.0'), True)
        self.assertEqual(packager.less_version('1.0.0-1', '2.0.0-0'), True)
        self.assertEqual(packager.less_version('2.0.0-1', '2.0.0-0'), False)
        self.assertEqual(packager.less_version('2.a', '2.b'), True)
        self.assertEqual(packager.less_version('2.b', '2.a'), False)


if __name__ == '__main__':
    unittest.main()

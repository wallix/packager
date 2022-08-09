#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from wallix_packager.packager import (read_config,
                                      replace_dict_all,
                                      normalize_config,
                                      extract_version_or_die,
                                      update_config_variables,
                                      ExtractedVersion,
                                      PackagerError)

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
            'a AA aa plop xY a AA aa A xY')

    def test_read_config(self):
        with open('tests/data/config1') as f:
            config = read_config(
                f, {'DIST_NAME':'debian', 'DIST_ID':'squeeze'})
        self.assertEqual(config, {
            'DIST_ID': 'squeeze',
            'DIST_NAME': 'debian',
            'X': '3',
            'VAR1': 'v1',
            'VAR2': 'v2',
            'VAR3': 'v3'
        })

    def test_normalize_config(self):
        config = {
            'DIST_ID': 'squeeze',
        }
        normalize_config(config)
        self.assertEqual(config, {
            'DIST_ID': 'squeeze',
            'PKG_DISTRIBUTION': 'squeeze',
        })

        config = {
            'DIST_ID': 'ubuntu',
        }
        normalize_config(config)
        self.assertEqual(config, {
            'DIST_ID': 'ubuntu',
            'PKG_DISTRIBUTION': 'unstable',
            'TARGET_NAME': '+ubuntu',
        })

        config = {
            'DIST_ID': 'squeeze',
            'PKG_DISTRIBUTION': 'buble',
        }
        normalize_config(config)
        self.assertEqual(config, {
            'DIST_ID': 'squeeze',
            'PKG_DISTRIBUTION': 'buble',
        })

    def test_update_config_variables(self):
        config = {'V':'x'}
        unparsed = update_config_variables(config, ['XYZ', 'X-Y', 'X=', 'ABC=123', 'V+=y'])
        self.assertEqual(config, {'V': 'xy', 'X': '', 'ABC': '123'})
        self.assertEqual(unparsed, ['XYZ', 'X-Y'])

    def test_extract_version_or_die(self):
        normalizer = lambda s: s
        content = '#abc\n#abc\nversion=123a b\nxyz'
        self.assertEqual(
            extract_version_or_die('version=(\d+\w+)', content, normalizer),
            ExtractedVersion('123a', (18, 22), content))

        with self.assertRaises(PackagerError):
            extract_version_or_die('^VERSION=(\d+\w+)', content, normalizer),
            ExtractedVersion('123a', (18, 22), content)


if __name__ == '__main__':
    unittest.main()

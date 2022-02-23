#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from wallix_packager.version import less_version

class TestVersion(unittest.TestCase):
    def test_less_version(self):
        self.assertEqual(less_version('1.0.0.0', '1.0.0.0'), False)
        self.assertEqual(less_version('0.0.9.0', '1.0.0.0'), True)
        self.assertEqual(less_version('1.0.0.0', '1.0.0.1'), True)
        self.assertEqual(less_version('1.0.0.1', '1.0.0.1'), False)
        self.assertEqual(less_version('1.0.0.1', '2.0.0.0'), True)
        self.assertEqual(less_version('1.0.0-1', '2.0.0-0'), True)
        self.assertEqual(less_version('2.0.0-1', '2.0.0-0'), False)
        self.assertEqual(less_version('2.a', '2.b'), True)
        self.assertEqual(less_version('2.b', '2.a'), False)


if __name__ == '__main__':
    unittest.main()

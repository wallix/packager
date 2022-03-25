#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from wallix_packager.shell import escape_shell_arg

class TestPackager(unittest.TestCase):
    def test_escape_shell_arg(self):
        self.assertEqual(escape_shell_arg(''), "''")
        self.assertEqual(escape_shell_arg('a'), "a")
        self.assertEqual(escape_shell_arg('abc'), "abc")
        self.assertEqual(escape_shell_arg('ééé'), "ééé")
        self.assertEqual(escape_shell_arg('[a]'), "'[a]'")
        self.assertEqual(escape_shell_arg('a*'), "'a*'")
        self.assertEqual(escape_shell_arg('a@d'), "a@d")
        self.assertEqual(escape_shell_arg(' a'), "' a'")
        self.assertEqual(escape_shell_arg("ab'c"), "'ab'\\''c'")


if __name__ == '__main__':
    unittest.main()

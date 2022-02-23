#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from wallix_packager.synchronizer import read_gitconfig, explode_git_url

class TestPulp(unittest.TestCase):
    def test_read_gitconfig(self):
        d = read_gitconfig('''
[core]
        repositoryformatversion = 0
        filemode = true
        bare = false
        logallrefupdates = true
[remote "origin"]
        url = git@gitlab.com:git/myrepo.git
        fetch = +refs/heads/*:refs/remotes/origin/*
[branch "master"]
        remote = origin
        merge = refs/heads/master
[submodule "modules/program_options"]
        active = true
        url = git@gitlab.com:git/program_options.git
[submodule "public"]
        active = true
        url = git@gitlab.com:git/redemption.git
[branch "b1"]
        remote = origin
        merge = refs/heads/b1
        '''.split('\n'))
        self.assertEqual(d, {
            'modules/program_options': 'git@gitlab.com:git/program_options.git',
            'public': 'git@gitlab.com:git/redemption.git',
        })

    def test_explode_git_url(self):
        self.assertEqual(explode_git_url('user1@gitlab.com:git/program_options.git'),
                         ('user1', 'gitlab.com', 'program_options.git'))

        self.assertEqual(explode_git_url('user1@gitlab.com:git/program_options'),
                         ('user1', 'gitlab.com', 'program_options'))

        self.assertEqual(explode_git_url('user1@gitlab.com:/program_options'), None)


if __name__ == '__main__':
    unittest.main()

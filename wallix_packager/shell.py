#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##
# Copyright (c) 2010-2022 WALLIX, SARL. All rights reserved.
# Licensed computer software. Property of WALLIX.
# Product name: Packager
# Author(s): Jonathan Poelen
##

import re
import subprocess
from typing import Dict, Tuple, Iterable


def shell_cmd(cmd: Iterable[str], env: Dict[str,str] = {'GIT_PAGER': ''}) -> str:
    print('$\x1b[34m', ' '.join(cmd), '\x1b[0m')
    return subprocess.check_output(cmd, env=env, text=True)


def git_uncommited_changes() -> str:
    return shell_cmd(['git', 'diff', '--shortstat'])


def git_tag_exists(tag: str) -> Tuple[bool, str]:
    # local tag
    tags = shell_cmd(['git', 'tag', '--list'])
    if tag in tags.split('\n'):
        return (True, 'local')

    # remote tag
    tags = shell_cmd(['git', 'ls-remote', '--tags', 'origin'])
    # tags contents:
    # 7b997fa58cd40848273c4b1469c787b0cdd69e84        refs/tags/9.1.33
    # dd3d667d68906c77e6fc47b5b8d19ff12fc47104        refs/tags/9.1.35
    #                                                          ^      \n
    if f'/{tag}\n' in tags:
        return (True, 'remote')

    return (False, '')


def git_last_tag() -> str:
    # tag-N-HASH
    tag = shell_cmd(['git', 'describe', '--tags'])
    pos = re.search(r'-\d+-\w+$', tag)
    return tag[:pos.start(0)]

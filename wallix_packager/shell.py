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
from typing import Dict, Tuple, Iterable, Optional

is_safe_word = re.compile('^[\w@./:,%@_=^]+$')

def escape_shell_arg(arg: str) -> str:
    if is_safe_word.match(arg) is None:
        arg = arg.replace("'", "'\\''")
        return f"'{arg}'"
    return arg

def shell_cmd(cmd: Iterable[str], env: Optional[Dict[str, str]] = None) -> str:
    print('$\x1b[34m', ' '.join(map(escape_shell_arg, cmd)), '\x1b[0m')
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
    m = re.search('-\\d+-[0-9a-f]{10}\n?$', tag)
    if m is None:
        return tag
    return tag[:m.start(0)]


def git_current_branch() -> str:
    # refs/heads/BRANCH
    branch = shell_cmd(['git', 'symbolic-ref', 'HEAD'])
    prefix = 'refs/heads/'
    return branch[len(prefix):-1] if branch.startswith(prefix) else branch[:-1]

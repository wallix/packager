#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##
# Copyright (c) 2010-2022 WALLIX, SARL. All rights reserved.
# Licensed computer software. Property of WALLIX.
# Product name: Packager
# Author(s): Jonathan Poelen
##

import re
import sys
import subprocess
from typing import Dict, Tuple, Sequence, Optional


is_safe_word = re.compile(r'^[-\w@./:,%@_=^]+$')


def escape_shell_arg(arg: str) -> str:
    if is_safe_word.match(arg) is None:
        arg = arg.replace("'", "'\\''")
        return f"'{arg}'"
    return arg


def print_cmd(cmd: Sequence[str]) -> None:
    print('$\x1b[34m', ' '.join(map(escape_shell_arg, cmd)), '\x1b[0m')


# TODO rename to output_shell
def shell_cmd(cmd: Sequence[str], env: Optional[Dict[str, str]] = None) -> str:
    print_cmd(cmd)
    return subprocess.check_output(cmd, env=env, text=True)


# TODO rename to run_shell
def shell_run(cmd: Sequence[str], env: Optional[Dict[str, str]] = None,
              check: bool = True) -> subprocess.CompletedProcess:
    print_cmd(cmd)
    return subprocess.run(cmd, env=env, check=check)


def errexit(msg) -> None:
    print(msg, file=sys.stderr)
    exit(1)


def getch() -> str:
    # unix version
    import tty, termios
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def confirm(msg: str) -> bool:
    print(f'{msg} [y/n] ', end='')
    sys.stdout.flush()
    ch = getch()
    print(ch)
    return ch == 'y'


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
    m = re.search('-\\d+-g[0-9a-f]{8,10}\n?$', tag)
    if m is None:
        return tag.strip()
    return tag[:m.start(0)]


def git_current_branch() -> str:
    # refs/heads/BRANCH
    branch = shell_cmd(['git', 'symbolic-ref', 'HEAD'])
    prefix = 'refs/heads/'
    return branch[len(prefix):-1] if branch.startswith(prefix) else branch[:-1]

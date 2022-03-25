#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##
# Copyright (c) 2010-2022 WALLIX, SARL. All rights reserved.
# Licensed computer software. Property of WALLIX.
# Product name: Packager
# Author(s): Christophe Grosjean, Jonathan Poelen, Raphael Zhou, Meng Tan
# Module description: Synchronize public submodule
##

import argparse
import os
import re
from typing import Dict, Tuple, Optional, Iterable
from .shell import shell_cmd


def fetch_clone(local_path: str, remote_path: str, ssh_address: str, cmd: str) -> None:
    print(f"== Synchronize {local_path} clone repository ==")
    shell_cmd(('ssh', ssh_address, f'cd {remote_path}; {cmd}'))


def set_commit(local_path: str, commit_hash: str) -> None:
    print(f"== Setting {local_path} repository to commit {commit_hash} ==")
    os.chdir(local_path)
    shell_cmd(('git', 'fetch'))
    shell_cmd(('git', 'reset', '--hard', commit_hash))


def set_tag(local_path: str, tag: str) -> None:
    print(f"== Setting {local_path} repository to tag {tag} ==")
    os.chdir(local_path)
    shell_cmd(('git', 'fetch', '--all'))
    shell_cmd(('git', 'reset', '--hard', f'tags/{tag}'))


def set_branch(local_path: str, branch: str):
    print(f"== Setting {local_path} repository to branch {branch} ==")
    os.chdir(local_path)
    shell_cmd(('git', 'fetch'))
    shell_cmd(('git', 'reset', '--hard', f'origin/{branch}'))


LocalPath = str
RemotePath = str
Addr = str
User = str

re_submodule = re.compile(r'^\s*\[submodule "([^"]+)"\]')
re_url = re.compile(r'^\s*url\s*=\s*([^#]+)')


def parse_gitconfig(lines: Iterable[str]) -> Dict[LocalPath, RemotePath]:
    d = {}

    local_path = None
    for line in lines:
        line = line.strip()

        m = re_submodule.match(line)
        if m is not None:
            local_path = m.group(1)
        elif line.startswith('['):
            local_path = None
        elif local_path:
            m = re_url.match(line)
            if m is not None:
                d[local_path] = m.group(1)

    return d


def read_gitconfig(filename: str = '.git/config') -> Dict[LocalPath, RemotePath]:
    with open(filename, encoding='utf-8') as f:
        return parse_gitconfig(f)


re_url_origin = re.compile('^([^@]+)@([^:]+):git/(.*)')


def explode_git_url(url: str) -> Optional[Tuple[User, Addr, RemotePath]]:
    m = re_url_origin.match(url)
    if m:
        return m.group(1), m.group(2), m.group(3)
    return None


def argument_parser(gitconfig: Dict[LocalPath, RemotePath],
                    description: str = 'Synchronize submodules') -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('submodule', nargs='+', help='last path is used', choices=gitconfig.keys())
    parser.add_argument('-s', '--sync-hook', nargs='?', metavar='CMD',
                        const='./custom_hooks/sync_repo.sh',
                        default='git fetch -p origin',
                        help='disabled that with an empty command')
    parser.add_argument('-u', '--username')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-b', '--branch')
    group.add_argument('-t', '--tag')
    group.add_argument('-c', '--commit-hash')

    return parser


def run_synchronizer(gitconfig: Dict[LocalPath, RemotePath], submodule_path: str, args: argparse.ArgumentParser) -> None:
    if args.sync_hook:
        if submodule_path not in gitconfig:
            raise Exception(f'Unknown config for {submodule_path}')

        infos = explode_git_url(gitconfig[submodule_path])
        if infos is None:
            raise Exception(f'Unknown config for {submodule_path}')

        user, addr, remote_path = infos
        fetch_clone(submodule_path, remote_path,
                    f'{args.username or user}@{addr}', args.sync_hook)

    if args.branch:
        set_branch(submodule_path, args.branch)
    elif args.tag:
        set_tag(submodule_path, args.tag)
    elif args.commit_hash:
        set_commit(submodule_path, args.commit_hash)

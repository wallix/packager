#!/usr/bin/env python3

import argparse
from typing import Callable, Optional
from .shell import confirm, shell_cmd, shell_run


def argument_parser(project_name: str, default_branch: str, description: str = '') -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-n', '--no-commit', action='store_true')
    parser.add_argument('-p', '--no-pull', action='store_true')
    parser.add_argument('-b', '--branch', default=default_branch, help=f'{project_name} branch')
    parser.add_argument('updated_repo_path', help=f'{project_name} path')
    return parser


def run_update_repo(update_repo: Callable[[], None],
                    project_name: str,
                    branch: str,
                    pull: bool,
                    commit_msg: Optional[str]) -> bool:
    if not confirm(f'Use "{branch}" branch for "{project_name}" ?'):
        return False

    shell_run(('git', 'fetch', '--tags', '--all', '-a'))
    shell_run(('git', 'switch', branch))

    if pull:
        shell_run(('git', 'pull', 'origin', branch, '--rebase'))

    update_repo()

    print(f'echo "{project_name}": git status before git commit -a')
    shell_run(('git', 'status', '-s'))

    if confirm('git diff ?'):
        shell_run(('git', 'diff'))

    if commit_msg:
        shell_run(('git', 'commit', '-am', commit_msg))

        if confirm(f'git push origin "{branch}" on "{project_name}" repository ?'):
            shell_run(('git', 'push', 'origin', branch))

    return True

#!/usr/bin/env python3

import argparse
from typing import Optional, Callable, TypeVar, Sequence
from .shell import confirm, shell_cmd


Ctx = TypeVar('Ctx')


class RepoUpdater:
    def __init__(self, project_name: str, default_branch: str, description: str = '') -> None:
        parser = argparse.ArgumentParser(description=description)
        parser.add_argument('-n', '--no-commit', action='store_true')
        parser.add_argument('-p', '--no-pull', action='store_true')
        parser.add_argument('-b', '--branch', default=default_branch, help=f'{project_name} branch')
        parser.add_argument('updated_repo_path', help=f'{project_name} path')
        self.parser = parser
        self.project_name = project_name

    def argument_parser(self) -> argparse.ArgumentParser:
        return self.parser

    def run(self,
            version: str,
            update_repo: Callable[[str, argparse.Namespace, Ctx], None],
            args: Optional[argparse.Namespace],
            update_args: Ctx) -> None:
        if args is None:
            args = self.parser.parse_args()

        if not confirm(f'Use "{args.branch}" branch for "{self.project_name}" ?'):
            self.parser.print_help()
            return

        shell_cmd(('git', 'fetch', '--tags', '--all', '-a'))
        shell_cmd(('git', 'switch', args.branch))

        if not args.no_pull:
            shell_cmd(('git', 'pull', 'origin', args.branch, '--rebase'))

        update_repo(version, args, update_args)

        print(f'echo "{self.project_name}": git status before git commit -a')
        shell_cmd(('git', 'status', '-s'))

        if confirm('git diff ?'):
            shell_cmd(('git', 'diff'))

        if not args.no_commit:
            shell_cmd(('git', 'commit' '-am', f'{self.project_name} updated to {version}'))

            if confirm(f'git push origin "{args.branch}" on "{self.project_name}" ?'):
                shell_cmd(('git', 'push', 'origin', args.branch))

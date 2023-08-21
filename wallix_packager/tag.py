import re
from typing import List

from .shell import (confirm,
                    errexit,
                    shell_cmd,
                    git_last_tag,
                    git_current_branch,
                    git_uncommited_changes,
                    )
from .version import (get_version_extractor,
                      re_match_version_to_tuple,
                      TypingVersion,
                      )
from .io import (readall, writeall)


def current_tag(repo_name: str, branch: str, ignore_change_and_not_pull: bool) -> str:
    current_branch = git_current_branch()

    if current_branch != branch:
        if not confirm(f'{repo_name}: {current_branch} '
                       f'branch is not {branch}, continue ?'):
            exit(1)

    shell_cmd(['git', 'fetch', '--all'])

    if not ignore_change_and_not_pull:
        changes = git_uncommited_changes()
        if changes:
            errexit(changes)

        shell_cmd(['git', 'pull', 'origin', current_branch, '--rebase'])

    return git_last_tag()


def parse_version(repo_name: str, tag: str) -> TypingVersion:
    patt = get_version_extractor()
    m = patt.match(tag)

    if m is None:
        errexit(f'{repo_name}: Invalid tag format: {tag}')

    return re_match_version_to_tuple(m)


def compute_suffix(repo_name: str, unofficial: str, current_suffix: str) -> str:
    if not current_suffix:
        return unofficial

    lastc = current_suffix[-1]

    if not ('a' <= lastc <= 'z'):
        errexit(f'{repo_name}: Invalid suffix: {current_suffix}')

    if lastc == 'z':
        lastc = 'za'
    else:
        lastc = chr(ord(lastc) + 1)

    return f'{current_suffix[:-2]}{lastc}'


def issues_from(tag: str) -> List[str]:
    msg = shell_cmd(['git', 'log', '--pretty=tformat:%s', f'{tag}..'])
    return sorted(set(re.findall(r'((?:\bWAB-|#)\d+)', msg)))


def update_version(pattern: re.Pattern, filename: str, new_version: str) -> None:
    contents = readall(filename)
    pos = pattern.search(contents).span(1)
    writeall(filename, f'{contents[:pos[0]]}{new_version}{contents[pos[1]:]}')
    git_push_version(new_version)


def git_push_version(version: str) -> None:
    shell_cmd(['git', 'commit', '-am', f'Version {version}'])
    shell_cmd(['git', 'tag', version])
    shell_cmd(['git', 'push'])
    shell_cmd(['git', 'push', '--follow-tags'])

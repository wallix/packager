#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import re
import shutil
import argparse
import datetime
import subprocess
from collections.abc import Iterable

var_ident = '[A-Z][A-Z0-9_]*'

def replace_dict_all(text:str, dico:dict[str,str]) -> str:
    rgx_replace_var = re.compile(f'%{var_ident}%')
    text_parts = []
    pos = 0
    for m in rgx_replace_var.finditer(text):
        text_parts.append(text[pos:m.start()])
        var = m.group()
        text_parts.append(dico.get(var[1:-1], var))
        pos = m.end()
    text_parts.append(text[pos:])
    return ''.join(text_parts)

def read_and_update_config(filename:str, configs:dict[str,str]=None) -> dict[str,str]:
    """ Parse target Config files """
    parse_config_rgx = re.compile(f'^({var_ident})\s*=(.*)')
    configs = {} if configs is None else configs

    with open(filename) as f:
        for line in f:
            if line.startswith('include '):
                directory = os.path.dirname(filename)
                included_path = os.path.join(directory, line[8:].strip())
                read_and_update_config(included_path, configs)
            elif m := re.search(parse_config_rgx, line):
                configs[m.group(1).strip()] = m.group(2).strip()

    if 'PKG_DISTRIBUTION' not in configs:
        if configs['DIST_NAME'].lower() == 'ubuntu':
            configs['PKG_DISTRIBUTION'] = 'unstable'
        else:
            configs['PKG_DISTRIBUTION'] = configs['DIST_ID']

    if 'TARGET_NAME' not in configs:
        if configs['DIST_NAME'].lower() == 'ubuntu':
            configs['TARGET_NAME'] = '+' + configs['DIST_ID']

    return configs

def update_config_variables(config:dict[str,str], variables:Iterable[str]) -> list[str]:
    """Return unparsed variable"""
    rgx_var = re.compile(f'^({var_ident})(\+?=)(.*)')
    variable_errors = []
    for var in variables:
        m = rgx_var.match(var)
        if m is None:
            variable_errors.append(var)
            continue
        k = m.group(1)
        newvalue = m.group(3) if m.group(2) == '=' else config.get(k, '') + m.group(3)
        config[k] = newvalue
    return variable_errors

def print_configs(configs:dict[str,str]) -> None:
    variables = []
    for k,v in configs.items():
        variables.append(f'{k} = {v}')
    print('\n'.join(variables))

def readall(filename:str) -> str:
    with open(filename) as f:
        return f.read()

def writeall(filename:str, s:str) -> None:
    with open(filename, 'w+') as f:
        f.write(s)

def get_changelog_entry(project_name:str, version:str, maintainer:str, urgency:str, utc:str) -> str:
    editor = os.environ.get('EDITOR') or 'nano'

    changelog = []

    tmp_changelog = f'/tmp/{version}-changelog.tmp'
    cmd = f'{editor} {tmp_changelog}'
    if os.system(cmd):
        raise Exception(f'Error in `{cmd}`')

    with open(tmp_changelog) as f:
        for line in f:
            if line and line != '\n':
                changelog.append('  * ')
                changelog.append(line)

    os.remove(tmp_changelog)

    if not changelog:
        raise Exception('Change log is empty')

    now = datetime.datetime.today().strftime(f'%a, %d %b %Y %H:%M:%S +{utc}')
    return (f'{project_name or "%PROJECT_NAME%"} ({version}%TARGET_NAME%) %PKG_DISTRIBUTION%; '
            f'urgency={urgency}\n\n{"".join(changelog)}\n\n -- {maintainer}  {now}\n\n')

def update_changelog(changelog_path:str, changelog:str) -> None:
    changelog += readall(changelog_path)
    writeall(changelog_path, changelog)

def create_build_directory(package_template:str, output_build:str) -> None:
    rgx_tempfile = re.compile('^#.*#$|~$')

    try:
        os.mkdir(output_build, 0o766)
    except FileExistsError:
        pass

    filenames = filter(lambda fname: rgx_tempfile.search(fname) is None,
                       os.listdir(package_template))

    for filename in filenames:
        out = readall(f'{package_template}/{filename}')
        out = replace_dict_all(out, configs)
        writeall(f'{output_build}/{filename}', out)

def less_version(lhs_version:str, rhs_version:str) -> bool:
    rgx_split_version = re.compile('[^\d]*(\d+)(?:\.(\d+))?(?:[-.](\d+))?(?:[-.](\d+))?(?:[-.](\d+))?(.*)')
    to_tuple = lambda m: (
        int(m.group(1)),
        int(m.group(2) or 0),
        int(m.group(3) or 0),
        int(m.group(4) or 0),
        int(m.group(5) or 0),
        m.group(6)
    )
    m1 = rgx_split_version.match(lhs_version)
    m2 = rgx_split_version.match(rhs_version)
    return to_tuple(m1) < to_tuple(m2)

def shell_cmd(cmd:list[str]) -> str:
    print('$', ' '.join(cmd))
    return subprocess.check_output(cmd, env={'GIT_PAGER':''}, text=True)

def git_uncommited_changes() -> str:
    return shell_cmd(['git', 'diff', '--shortstat'])

def git_tag_exists(tag:str) -> tuple[bool, str]:
    tag = tag+'\n'

    # local tag
    tags = shell_cmd(['git', 'tag', '--list'])
    if tag in tags:
        return (True, 'local')

    # remote tag
    tags = shell_cmd(['git', 'ls-remote', '--tags', 'origin'])
    if '/' + tag in tags:
        return (True, 'remote')

    return (False, '')

def git_last_tag() -> str:
    return shell_cmd(['git', 'describe', '--tags']).partition('\n')[0]

def regex_version_or_die(pattern:str, errcode:int) -> re.Pattern:
    try:
        return re.compile(pattern)
    except re.error as e:
        print('Regex version:', e, file=sys.stderr)
        exit(errcode)

def read_version_or_die(pattern:str, file_version:str, errcode:int) -> tuple[str, str]:
    if not file_version:
        print('File version is empty', file=sys.stderr)
        exit(errcode)

    rgx_version = regex_version_or_die(pattern, errcode)
    content = readall(file_version)

    m = rgx_version.match(content)

    if m is None:
        print(f'Version not found (pattern is {pattern})', file=sys.stderr)
        exit(errcode)

    return m.group(1), m.span(1), content

def argument_parser(description:str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Packager for proxies repositories')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-b', '--build', action='store_true', help='create a package directory')
    group.add_argument('-g', '--get-version', action='store_true')
    group.add_argument('-n', '--new-version', metavar='VERSION', help='update version and create a tag')
    group.add_argument('--show-config', action='store_true', help='show configs')

    parser.add_argument('--no-check-uncommited', action='store_true')
    parser.add_argument('--check-uncommited', dest='no_check_uncommited', action='store_false')

    group = parser.add_argument_group('Version options')
    group.add_argument('--file-version', metavar='PATH')
    group.add_argument('--pattern-version', metavar='REGEX',
                       default='\s*(?:[a-zA-Z_][a-zA-Z0-9_]*)?VERSION\s*=\s*[\'"]([^\'"]*)[\'"]',
                       help='pattern for version')

    group = parser.add_argument_group('Update version and tag')
    group.add_argument('--force-version', action='store_true')
    group.add_argument('--no-commit-and-tag', action='store_true')
    group.add_argument('--commit-and-tag', dest='no_commit_and_tag', action='store_false')
    group.add_argument('--no-push', action='store_true')
    group.add_argument('--push', dest='no_push', action='store_false')
    group.add_argument('--commit-message', metavar='TEMPLATE', default='Version %s', action='store_false',
                       help='commit message template, %s is replaced with new version')

    group = parser.add_argument_group('Build package options')
    group.add_argument('--target', metavar='NAME', help='target file path')
    group.add_argument('--output-build', metavar='DIRNAME', default='debian', help='build directory')
    group.add_argument('--clean-build', action='store_true', help='remove existing build directory')
    group.add_argument('--package-template', metavar='DIRNAME',
                       default='packaging/template/debian', help='package template directory')
    group.add_argument('--build-package', action='store_true', help='run dpkg-buildpackage')
    group.add_argument('--project-name', metavar='NAME')
    group.add_argument('--project-version', metavar='VERSION')
    group.add_argument('--update-changelog', action='store_true')
    group.add_argument('--urgency', default='low')
    group.add_argument('--utc', default='0200')
    group.add_argument('--maintainer', default='Proxies Team <R&D-Project-Bastion-Proxies@wallix.com>')
    group.add_argument('--distribution-name')
    group.add_argument('--distribution-version')
    group.add_argument('--distribution-id')
    group.add_argument('--package-distribution')
    group.add_argument('--no-check-version', action='store_true')
    group.add_argument('--check-version', dest='no_check_version', action='store_false')
    group.add_argument('-s', '--variable', metavar='VARIABLE=VALUE', action='append', default=[],
                       help='support of VARIABLE=VALUE and VARIABLE+=VALUE')

    return parser

class Hook:
    def normalize_version(self, version:str) -> str:
        """normalized version from file"""
        return version

    def sanitize_version(self, old_version:str, new_version:str) -> str:
        """convert to a writable version"""
        return new_version

    def post_updated_version(self, old_version:str, new_version:str) -> None:
        pass

def run_packager(args, hooks:Hook=Hook()) -> None:
    if not args.show_config and not args.get_version and not args.no_check_uncommited:
        changes = git_uncommited_changes()
        if changes:
            print(f'Your repository has uncommited changes:\n{changes}\n'
                  'Please commit before packaging or use --no-check-uncommited', file=sys.stderr)
            exit(11)

    # get version
    new_version = args.new_version
    if args.get_version or new_version is not None:
        results = read_version_or_die(args.pattern_version, args.file_version, 1)
        print(hook.normalize_version(results[0]))
        exit(0)

    # set version
    if new_version is not None:
        if not new_version:
            print(f'New version is empty', file=sys.stderr)
            exit(2)

        version, pos, content = read_version_or_die(args.pattern_version, args.file_version, 1)
        version = hook.normalize_version(version)

        if not args.force_version and not less_version(version, new_version):
            print(f'New version ({new_version}) is less than old version ({version})',
                  file=sys.stderr)
            exit(3)

        new_version = hook.sanitize_version(version, new_version)

        tag_exists, tag_cat = git_tag_exists(new_version)
        if tag_exists:
            print(f'Tag {new_version} already exists ({tag_cat})', file=sys.stderr)
            exit(4)

        writeall(args.file_version,
                 f'{content[:pos[0]]}{new_version}{content[pos[1]:]}')
        hook.post_updated_version(version, new_version)

        if not args.no_commit_and_tag:
            shell_cmd(['git', 'commit', '-am', args.commit_message % (new_version,)])
            shell_cmd(['git', 'tag', new_version])
            if not args.no_push:
                shell_cmd(['git', 'push'])
                shell_cmd(['git', 'push', '--tags'])
        exit(0)

    if not args.target:
        print('--target is missing', file=sys.stderr)
        exit(1)

    # Build / Show config
    if not args.distribution_name or not args.distribution_version or not args.distribution_id:
        import distro
        args.distribution_id = args.distribution_id or distro.name()
        args.distribution_name = args.distribution_name or distro.id()
        args.distribution_version = args.distribution_version or distro.version()

    configs = {
        'PKG_DISTRIBUTION': args.package_distribution,
        'DIST_ID': args.distribution_id,
        'DIST_NAME': args.distribution_name,
        'DIST_VERSION': args.distribution_version,
        'PROJECT_VERSION': args.project_version,
        'PROJECT_NAME': args.project_name,
        'URGENCY': args.urgency,
        'MAINTAINER': args.maintainer,
        'ARCH': 'any',
        'TARGET_NAME': '',
        'UTC': args.utc or '0200',
    }

    read_and_update_config(args.target, configs)

    variable_errors = update_config_variables(configs, args.variable)
    if variable_errors:
        print('Parse error on -s / --variable: "', '", "'.join(variable_errors), '"',
              sep='', file=sys.stderr)
        exit(20)

    if args.show_config:
        print_configs(configs)
        exit(0)

    project_version = configs['PROJECT_VERSION']
    project_name = configs['PROJECT_NAME']

    if not args.no_check_version or not project_version:
        results = read_version_or_die(args.pattern_version, args.file_version, 3)
        version = hook.normalize_version(results[0])
        if not project_version:
            project_version = version
        elif not args.no_check_version and (project_version != version or project_version != git_last_tag()):
            print('Repository head mismatch current version. Ignored with --no-check-version', file=sys.stderr)
            exit(4)
    elif project_version:
        project_version = hook.normalize_version(project_version)

    if not project_version or not project_name:
        if not project_version:
            print('--project-version or -s PROJECT_VERSION=... is missing', file=sys.stderr)
        if not project_name:
            print('--project-name or -s PROJECT_NAME=... is missing', file=sys.stderr)
        exit(2)

    if args.update_changelog:
        changelog = get_changelog_entry(project_name,
                                        project_version,
                                        configs['MAINTAINER'],
                                        configs['URGENCY'],
                                        configs['UTC'])
        update_changelog(f'{args.package_template}/changelog', changelog)

    if args.clean_build:
        try:
            shutil.rmtree(args.output_build)
        except:
            pass

    create_build_directory(args.package_template, args.output_build)

    if args.build_package:
        status = os.system('dpkg-buildpackage -b -tc -us -uc -r')
        if status:
            print('Build failed: dpkg-buildpackage error', file=sys.stderr)
            exit(5)

if __name__ == '__main__':
    parser = argument_parser('Packager for proxies repositories')
    args = parser.parse_args()
    run_packager(args)

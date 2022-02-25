#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##
# Copyright (c) 2010-2022 WALLIX, SARL. All rights reserved.
# Licensed computer software. Property of WALLIX.
# Product name: Packager
# Author(s): Christophe Grosjean, Jonathan Poelen, Raphael Zhou, Meng Tan
# Module description: Create package and git tag
##

import sys
import os
import re
import shutil
import argparse
import datetime
import subprocess
from typing import Dict, Tuple, Iterable
from .io import writeall, readall
from .version import less_version
from .shell import shell_cmd, git_uncommited_changes, git_tag_exists, git_last_tag

var_ident = '[A-Z][A-Z0-9_]*'


class PackagerError(Exception):
    pass


def replace_dict_all(text: str, dico: Dict[str, str]) -> str:
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


def read_and_update_config(filename: str, configs: Dict[str, str] = None) -> Dict[str, str]:
    """ Parse target Config files """
    parse_config_rgx = re.compile(rf'^({var_ident})\s*=(.*)')
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


def update_config_variables(config: Dict[str, str], variables: Iterable[str]) -> list[str]:
    """Return unparsed variable"""
    rgx_var = re.compile(rf'^({var_ident})(\+?=)(.*)')
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


def print_configs(configs: Dict[str, str]) -> None:
    variables = []
    for k, v in configs.items():
        variables.append(f'{k} = {v}')
    print('\n'.join(variables))


def get_changelog_entry(project_name: str, version: str, maintainer: str, urgency: str, utc: str) -> str:
    editor = os.environ.get('EDITOR') or 'nano'

    changelog = []

    tmp_changelog = f'/tmp/{version}-changelog.tmp'
    cmd = f'{editor} {tmp_changelog}'
    if os.system(cmd):
        raise PackagerError(f'Error in `{cmd}`')

    with open(tmp_changelog) as f:
        for line in f:
            if line and line != '\n':
                changelog.append('  * ')
                changelog.append(line)

    os.remove(tmp_changelog)

    if not changelog:
        raise PackagerError('Change log is empty')

    now = datetime.datetime.today().strftime(f'%a, %d %b %Y %H:%M:%S +{utc}')
    return (f'{project_name or "%PROJECT_NAME%"} ({version}%TARGET_NAME%) %PKG_DISTRIBUTION%; '
            f'urgency={urgency}\n\n{"".join(changelog)}\n\n -- {maintainer}  {now}\n\n')


def update_changelog(changelog_path: str, changelog: str) -> None:
    changelog += readall(changelog_path)
    writeall(changelog_path, changelog)


def create_build_directory(package_template: str, output_build: str, configs: Dict[str, str]) -> None:
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


def check_version(old_version: str, new_version: str) -> None:
    if not less_version(old_version, new_version):
        raise PackagerError(f'New version ({new_version}) is less than'
                            f' old version ({old_version})')


def check_pattern_version(old_version: str, new_version: str, pattern: str) -> None:
    if pattern:
        m = re.match(pattern, old_version)
        if m is None:
            raise PackagerError('Unable to retrieve the version number'
                                f'from {old_version}')
        if not new_version.startswith(m.group(0)):
            raise PackagerError(f'The last tag number ({old_version}) of '
                                f'the repository is not compatible with'
                                f'the new tag number {new_version}. '
                                f'Pattern is "{pattern}"')


def regex_version_or_die(pattern: str) -> re.Pattern:
    try:
        return re.compile(pattern)
    except re.error as e:
        tb = sys.exc_info()[2]
        raise PackagerError(
            f'Invalid error on regex version: {pattern}').with_traceback(tb)


def read_version_or_die(pattern: str, file_version: str) -> Tuple[str, Tuple[int,int], str]:
    if not file_version:
        raise PackagerError('File version is empty')

    rgx_version = regex_version_or_die(pattern)
    content = readall(file_version)

    m = rgx_version.match(content)

    if m is None:
        raise PackagerError(
            f'Version not found: file={file_version}  pattern={pattern}')

    return m.group(1), m.span(1), content


def argument_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Packager for proxies repositories')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-b', '--build', action='store_true',
                       help='create a package directory')
    group.add_argument('-g', '--get-version', action='store_true')
    group.add_argument('-n', '--new-version', metavar='VERSION',
                       help='update version and create a tag')
    group.add_argument('--show-config', action='store_true',
                       help='show configs')

    parser.add_argument('--no-check-uncommited', action='store_true')
    parser.add_argument('--check-uncommited',
                        dest='no_check_uncommited', action='store_false')

    group = parser.add_argument_group('Version options')
    group.add_argument('--file-version', metavar='PATH')
    group.add_argument('--pattern-version', metavar='REGEX',
                       default=r'\s*(?:[a-zA-Z_][a-zA-Z0-9_]*)?VERSION\s*=\s*[\'"]([^\'"]*)[\'"]',
                       help='pattern for version')

    group = parser.add_argument_group('Update version and tag')
    group.add_argument('--force-version', action='store_true')
    group.add_argument('--start-pattern-version', default=r'^\d+\.\d+\.',
                       help='new version and current version must be the same')
    group.add_argument('--no-commit-and-tag', action='store_true')
    group.add_argument('--commit-and-tag',
                       dest='no_commit_and_tag', action='store_false')
    group.add_argument('--no-push', action='store_true')
    group.add_argument('--push', dest='no_push', action='store_false')
    group.add_argument('--commit-message', metavar='TEMPLATE', default='Version %s',
                       help='commit message template, %s is replaced with new version')

    group = parser.add_argument_group('Build package options')
    group.add_argument('--target', metavar='NAME', help='target file path')
    group.add_argument('--output-build', metavar='DIRNAME',
                       default='debian', help='build directory')
    group.add_argument('--clean-build', action='store_true',
                       help='remove existing build directory')
    group.add_argument('--package-template', metavar='DIRNAME',
                       default='packaging/template/debian', help='package template directory')
    group.add_argument('--build-package', action='store_true',
                       help='run dpkg-buildpackage')
    group.add_argument('--project-name', metavar='NAME')
    group.add_argument('--project-version', metavar='VERSION')
    group.add_argument('--update-changelog', action='store_true')
    group.add_argument('--urgency', default='low')
    group.add_argument('--utc', default='0200')
    group.add_argument('--maintainer',
                       default='Proxies Team <R&D-Project-Bastion-Proxies@wallix.com>')
    group.add_argument('--distribution-name')
    group.add_argument('--distribution-version')
    group.add_argument('--distribution-id')
    group.add_argument('--package-distribution')
    group.add_argument('--no-check-version', action='store_true')
    group.add_argument('--check-version',
                       dest='no_check_version', action='store_false')
    group.add_argument('-s', '--variable', metavar='VARIABLE=VALUE', action='append', default=[],
                       help='support of VARIABLE=VALUE and VARIABLE+=VALUE')

    return parser


class Hook:
    def normalize_version(self, version: str) -> str:
        """normalized version from file"""
        return version

    def sanitize_version(self, old_version: str, new_version: str) -> str:
        """convert to a writable version"""
        return new_version

    def post_updated_version(self, old_version: str, new_version: str) -> None:
        pass


def run_packager(args: argparse.ArgumentParser, hook: Hook = Hook()) -> None:
    if not args.show_config and not args.get_version and not args.no_check_uncommited:
        changes = git_uncommited_changes()
        if changes:
            raise PackagerError(f'Your repository has uncommited changes:\n{changes}\n'
                                'Please commit before packaging or use --no-check-uncommited')

    # get version
    new_version = args.new_version
    if args.get_version or new_version is not None:
        results = read_version_or_die(args.pattern_version, args.file_version)
        print(hook.normalize_version(results[0]))
        return

    # set version
    if new_version is not None:
        if not new_version:
            raise PackagerError(f'New version is empty')

        version, pos, content = read_version_or_die(
            args.pattern_version, args.file_version)
        version = hook.normalize_version(version)

        if not args.force_version:
            check_version(version, new_version)
            check_pattern_version(version, new_version,
                                  args.start_pattern_version)

        new_version = hook.sanitize_version(version, new_version)

        tag_exists, tag_cat = git_tag_exists(new_version)
        if tag_exists:
            raise PackagerError(
                f'Tag {new_version} already exists ({tag_cat})')

        writeall(args.file_version,
                 f'{content[:pos[0]]}{new_version}{content[pos[1]:]}')
        hook.post_updated_version(version, new_version)

        if not args.no_commit_and_tag:
            shell_cmd(['git', 'commit', '-am',
                       args.commit_message % (new_version,)])
            shell_cmd(['git', 'tag', new_version])
            if not args.no_push:
                shell_cmd(['git', 'push'])
                shell_cmd(['git', 'push', '--tags'])
        return

    if not args.target:
        raise PackagerError('--target is missing')

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
        errors_s = '", "'.join(variable_errors)
        raise PackagerError(f'Parse error on -s / --variable: "{errors_s}"')

    if args.show_config:
        print_configs(configs)
        return

    project_version = configs['PROJECT_VERSION']
    project_name = configs['PROJECT_NAME']

    if not args.no_check_version or not project_version:
        results = read_version_or_die(args.pattern_version, args.file_version)
        version = hook.normalize_version(results[0])
        if not project_version:
            project_version = version
        elif not args.no_check_version and (project_version != version or project_version != git_last_tag()):
            raise PackagerError('Repository head mismatch current version. '
                                'Ignored with --no-check-version')
    elif project_version:
        project_version = hook.normalize_version(project_version)

    if not project_version or not project_name:
        errors = []
        if not project_version:
            errors.append(
                '--project-version or -s PROJECT_VERSION=... is missing')
        if not project_name:
            errors.append('--project-name or -s PROJECT_NAME=... is missing')
        raise PackagerError(', '.join(errors))

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
        except OSError:
            pass

    create_build_directory(args.package_template, args.output_build, configs)

    if args.build_package:
        status = os.system('dpkg-buildpackage -b -tc -us -uc -r')
        if status:
            raise PackagerError('Build failed: dpkg-buildpackage error')

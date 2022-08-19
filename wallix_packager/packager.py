#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##
# Copyright (c) 2010-2022 WALLIX, SARL. All rights reserved.
# Licensed computer software. Property of WALLIX.
# Product name: Packager
# Author(s): Christophe Grosjean, Jonathan Poelen, Raphael Zhou, Meng Tan
# Module description: Create package and git tag
##

import os
import re
import shutil
import argparse
import datetime
from typing import (Dict, Tuple, List, Iterable,
                    NamedTuple, Optional, TextIO, Callable)
from .io import writeall, readall
from .version import less_version
from .shell import git_uncommited_changes, git_last_tag, shell_run
from .synchronizer import chdir
from .repo_updater import run_update_repo

var_ident = '[A-Z][A-Z0-9_]*'

DEFAULT_PATTERN_VERSION = r'(?:[a-zA-Z_][a-zA-Z0-9_]*)?VERSION\b\s*(?:=\s*)?[\'"]?([^\'" ]*)'

DEFAULT_BRANCH = os.environ.get('DEFAULT_BRANCH')
DEFAULT_REPO_NAME = os.environ.get('DEFAULT_REPO_NAME', '')
DEFAULT_UPDATED_REPO_BRANCH = os.environ.get('DEFAULT_UPDATED_REPO_BRANCH')
DEFAULT_UPDATED_REPO_NAME = os.environ.get('DEFAULT_UPDATED_REPO_NAME', 'updated')


def build_reference_pattern(pattern: Optional[str], application_name: Optional[str]) -> re.Pattern:
    if not pattern:
        prefix = application_name or DEFAULT_REPO_NAME
        if prefix:
            raise PackagerError(
                '--pattern-reference is missing'
                ' (or set --application-name or DEFAULT_REPO_NAME environment variable)')
        pattern = fr'{prefix}_?(?:[vV]ersion|VERSION|[tT]ag|TAG)?\b\s*(?:=\s*)?[\'"]?([^\'" ]*)'
    return re.compile(pattern)


class PackagerError(Exception):
    pass


class DistributionInfos(NamedTuple):
    distribution_id: str
    distribution_name: str
    distribution_version: str


def distribution_infos(load_infos: bool,
                       distribution_id: Optional[str],
                       distribution_name: Optional[str],
                       distribution_version: Optional[str]) -> DistributionInfos:
    if load_infos:
        import distro
        if distribution_id is None:
            distribution_id = distro.id()
        if distribution_name is None:
            distribution_name = distro.name()
        if distribution_version is None:
            distribution_version = distro.version()

    return DistributionInfos(
        distribution_id=distribution_id or '',
        distribution_name=distribution_name or '',
        distribution_version=distribution_version or ''
    )


def replace_dict_all(text: str, variables: Dict[str, str]) -> str:
    rgx_replace_var = re.compile(f'%{var_ident}%')
    text_parts = []
    pos = 0
    for m in rgx_replace_var.finditer(text):
        text_parts.append(text[pos:m.start()])
        var = m.group()
        text_parts.append(variables.get(var[1:-1], ''))
        pos = m.end()
    text_parts.append(text[pos:])
    return ''.join(text_parts)


def _read_config(config_file: TextIO,
                 encoding: str,
                 config: Dict[str, str],
                 parse_config_rgx: re.Pattern) -> None:
    for line in config_file:
        if line.startswith('include '):
            directory = os.path.dirname(config_file.name)
            included_path = os.path.join(directory, line[8:].strip())
            with open(included_path, encoding=encoding) as f:
                _read_config(f, encoding, config, parse_config_rgx)
        else:
            m = re.match(parse_config_rgx, line)
            if m is not None:
                config[m.group(1).strip()] = m.group(2).strip()


def read_config(config_file: TextIO,
                config: Optional[Dict[str, str]] = None,
                encoding: str = 'utf-8') -> Dict[str, str]:
    """ Parse target Config files """
    parse_config_rgx = re.compile(rf'^({var_ident})\s*=(.*)')
    config = {} if config is None else config

    _read_config(config_file, encoding, config, parse_config_rgx)
    return config


def normalize_config(config: Dict[str, str]) -> None:
    if config.get('PKG_DISTRIBUTION') is None:
        dist_id = config.get('DIST_ID')
        if dist_id == 'ubuntu':
            config['PKG_DISTRIBUTION'] = 'unstable'
        elif dist_id is not None:
            config['PKG_DISTRIBUTION'] = dist_id

    if config.get('TARGET_NAME') is None:
        dist_id = config.get('DIST_ID')
        if dist_id == 'ubuntu':
            config['TARGET_NAME'] = f'+{dist_id}'


def update_config_variables(config: Dict[str, str], variables: Iterable[str]) -> List[str]:
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


def print_config(config: Dict[str, str]) -> None:
    print('\n'.join(f'{k} = {v}' for k, v in config.items()))


def get_changelog_entry(project_name: str,
                        version: str,
                        maintainer: str,
                        urgency: str,
                        utc: str,
                        encoding: str = 'utf-8') -> str:
    editor = os.environ.get('EDITOR') or 'nano'

    changelog = []

    tmp_changelog = f'/tmp/{version}-changelog.tmp'
    cmd = f'{editor} {tmp_changelog}'
    if os.system(cmd):
        raise PackagerError(f'Error in `{cmd}`')

    with open(tmp_changelog, encoding=encoding) as f:
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


def prepare_build_files(
        filename: str,
        extra_config: Dict[str, Dict[str, str]],
        config: Dict[str, str]
) -> List[Tuple[str, Dict[str, str]]]:
    dest_filenames_config = [(filename, config)]
    if not extra_config:
        return dest_filenames_config

    project_name = config['PROJECT_NAME']
    if filename.endswith(".service"):
        dest_filenames_config = [
            ("%s-%s.%s" % (prefix,
                           project_name,
                           filename),
             extra_config[prefix])
            for prefix in extra_config
        ]
    elif filename.startswith(f"{project_name}."):
        dest_filenames_config = [
            ("%s-%s" % (prefix, filename),
             extra_config[prefix])
            for prefix in extra_config
        ]
    return dest_filenames_config


def create_build_directory(package_template_dir: str,
                           output_build: str,
                           config: Dict[str, str]) -> None:
    try:
        os.mkdir(output_build, 0o766)
    except FileExistsError:
        pass

    rgx_tempfile = re.compile('^#.*#$|~$')
    filenames = filter(lambda fname: rgx_tempfile.match(fname) is None,
                       os.listdir(package_template_dir))

    from .pybuild import pybuild_parameters
    extra_config = pybuild_parameters(config)
    file_dest_configs = (
        (filename, dest_filename, dest_config)
        for filename in filenames
        for dest_filename, dest_config in prepare_build_files(
            filename,
            extra_config,
            config
        )
    )
    for filename, dest_filename, dest_config in file_dest_configs:
        out = readall(f'{package_template_dir}/{filename}')
        out = replace_dict_all(out, dest_config)
        writeall(f'{output_build}/{dest_filename}', out)


def remove_directory(directory: str) -> None:
    try:
        shutil.rmtree(directory)
    except OSError:
        pass


def regex_version_or_die(pattern: str) -> re.Pattern:
    try:
        return re.compile(pattern)
    except re.error as e:
        raise PackagerError(f'Invalid error on regex version: {pattern}') from e


class ExtractedVersion(NamedTuple):
    version: str
    position: Tuple[int, int]
    original_text: str

def extract_version_or_die(pattern: str, text: str,
                           normalizer: Callable[[str], str]) -> ExtractedVersion:
    rgx_version = regex_version_or_die(pattern)

    m = rgx_version.search(text)

    if m is None:
        raise PackagerError(f"Version not found\npattern = {pattern}")

    return ExtractedVersion(
        version=normalizer(m.group(1)),
        position=m.span(1),
        original_text=text
    )


def read_version_from_file_or_die(pattern: str,
                                  version_file: TextIO,
                                  normalizer: Callable[[str], str]) -> str:
    try:
        return extract_version_or_die(pattern,
                                      version_file.read(),
                                      normalizer
                                      ).version
    except PackagerError as e:
        raise PackagerError(f'{e}\nfilename = {version_file.name}')


def add_arguments_for_get_version_command(parser: argparse.ArgumentParser,
                                          required: bool = True) -> None:
    parser.add_argument('-V', '--version-file', metavar='PATH', required=required,
                        type=argparse.FileType('r', encoding='utf-8'),
                        help='file that contains the version to be extracted')
    parser.add_argument('-P', '--pattern-version', metavar='REGEX',
                        default=DEFAULT_PATTERN_VERSION,
                        help='pattern for version extractor')


def add_arguments_for_show_config_command(parser: argparse.ArgumentParser) -> None:
    add_arguments_for_get_version_command(parser, required=False)
    parser.add_argument('-t', '--target-file', metavar='NAME',
                        type=argparse.FileType('r', encoding='utf-8'),
                        help='target file path')

    parser.add_argument('-n', '--project-name', metavar='NAME')
    parser.add_argument('-v', '--project-version', metavar='VERSION')

    parser.add_argument('-D', '--package-distribution')

    parser.add_argument('--maintainer',
                        default='Proxies Team <R&D-Project-Bastion-Proxies@wallix.com>')

    parser.add_argument('--distribution-id')
    parser.add_argument('--distribution-name')
    parser.add_argument('--distribution-version')
    # py-3.9: action=argparse.BooleanOptionalAction
    parser.add_argument('--load-distribution-infos', action='store_true')

    parser.add_argument('--urgency', default='low')
    parser.add_argument('--utc', default='0200')
    parser.add_argument('--arch', default='any')

    parser.add_argument('-s', '--variable', metavar='VARIABLE=VALUE', action='append', default=[],
                        help='support of VARIABLE=VALUE and VARIABLE+=VALUE')


def add_arguments_for_build_command(parser: argparse.ArgumentParser) -> None:
    add_arguments_for_show_config_command(parser)

    group = parser.add_argument_group('Output options')
    group.add_argument('-o', '--output-build', metavar='DIRNAME',
                       default='debian', help='build directory')
    group.add_argument('--no-clean', action='store_true',
                       help='remove build directory after build')
    group.add_argument('-d', '--package-template-dir', metavar='DIRNAMES',
                       nargs='+', default=['packaging/template/debian'],
                       help='package template directory')
    group.add_argument('-b', '--build-package', action='store_true',
                       help='run dpkg-buildpackage')
    group.add_argument('--use-pybuild', action='store_true',
                       help='This option is deprecated')

    group = parser.add_argument_group('Git integration options')
    # py-3.9: action=argparse.BooleanOptionalAction
    parser.add_argument('--no-check', action='store_true',
                        help='disable all git options')
    parser.add_argument('--no-check-uncommited', action='store_false',
                        dest='check_uncommited')
    parser.add_argument('--check-uncommited', action='store_true')
    parser.add_argument('--no-check-version', action='store_false',
                        dest='check_version')
    parser.add_argument('--check-version', action='store_true')


def add_arguments_for_sync_tag_command(parser: argparse.ArgumentParser,
                                       require_updated_repo_path: bool = True) -> None:
    add_arguments_for_get_version_command(parser, required=False)

    parser.add_argument('--reference-file', metavar='PATH',
                        help=f'file that contains the reference version on {DEFAULT_REPO_NAME}.'
                             f' Is relative to -u/--{DEFAULT_UPDATED_REPO_NAME}-path')
    parser.add_argument('--pattern-reference', metavar='REGEX',
                        help=f'pattern for reference tag updater')

    parser.add_argument('-B', f'--{DEFAULT_UPDATED_REPO_NAME}-branch', metavar='BRANCH',
                        dest='updated_repo_branch', default=DEFAULT_UPDATED_REPO_BRANCH,
                        required=DEFAULT_UPDATED_REPO_BRANCH is None)
    # py-3.9: action=argparse.BooleanOptionalAction
    parser.add_argument('-n', f'--no-{DEFAULT_UPDATED_REPO_NAME}-commit', action='store_true',
                        dest='no_pull_for_updated_repo')
    # py-3.9: action=argparse.BooleanOptionalAction
    parser.add_argument('-p', f'--no-{DEFAULT_UPDATED_REPO_NAME}-pull', action='store_true',
                        dest='no_commit_for_updated_repo')
    # py-3.9: action=argparse.BooleanOptionalAction
    parser.add_argument('-g', '--ignore-change-and-not-pull', action='store_true')
    parser.add_argument('--application-name', default=DEFAULT_REPO_NAME,
                        required=DEFAULT_REPO_NAME is None)
    parser.add_argument('-u', f'--{DEFAULT_UPDATED_REPO_NAME}-path',
                        dest='updated_repo_path',
                        required=require_updated_repo_path)


def add_arguments_for_create_tag_command(parser: argparse.ArgumentParser) -> None:
    add_arguments_for_sync_tag_command(parser, False)

    parser.add_argument('-b', '--branch', metavar='BRANCH',
                        default=DEFAULT_BRANCH,
                        required=DEFAULT_BRANCH is None)
    # py-3.9: action=argparse.BooleanOptionalAction
    parser.add_argument('-U', f'--no-{DEFAULT_UPDATED_REPO_NAME}-update', action='store_true',
                        dest='no_update_for_updated_repo')

    parser.add_argument('--update-changelog', action='store_true')


class Hook:
    def normalize_version(self, version: str) -> str:
        """normalized version from file"""
        return version

    def update_repo(self, version: str, project_path: str, args: argparse.Namespace) -> None:
        if not args.reference_file:
            raise PackagerError('--reference-file is missing')
        self.basic_update_repo(version,
                               args.reference_file,
                               build_reference_pattern(args.pattern_reference,
                                                       args.application_name))

    def basic_update_repo(self, version: str, reference_filename: str, regex: re.Pattern) -> None:
        content = readall(reference_filename)

        m = regex.search(content)
        if m is None:
            raise PackagerError(
                'Reference version not found\n'
                f'pattern = {regex.pattern}\n'
                f'filename = {reference_filename}')

        pos = m.span(1)
        writeall(reference_filename,
                 f'{content[:pos[0]]}{version}{content[pos[1]:]}')


def cmd_show_version(args: argparse.Namespace, hook: Hook) -> None:
    version = read_version_from_file_or_die(args.pattern_version,
                                            args.version_file,
                                            hook.normalize_version)
    print(version)


def make_config(args: argparse.Namespace) -> Dict[str, str]:
    dist_infos = distribution_infos(load_infos=args.load_distribution_infos,
                                    distribution_id=args.distribution_id,
                                    distribution_name=args.distribution_name,
                                    distribution_version=args.distribution_version)

    config = dict(filter(
        lambda t: t[1] is not None,
        (
            ('DIST_ID', dist_infos.distribution_id),
            ('DIST_NAME', dist_infos.distribution_name),
            ('DIST_VERSION', dist_infos.distribution_version),
            ('PKG_DISTRIBUTION', args.package_distribution),
            ('PROJECT_VERSION', args.project_version),
            ('PROJECT_NAME', args.project_name),
            ('URGENCY', args.urgency),
            ('MAINTAINER', args.maintainer),
            ('ARCH', args.arch),
            ('UTC', args.utc or '0200'),
        )
    ))

    if args.target_file is not None:
        read_config(args.target_file, config)

    variable_errors = update_config_variables(config, args.variable)
    if variable_errors:
        errors = '", "'.join(variable_errors)
        raise PackagerError(f'Parse error on -s / --variable: "{errors}"')

    normalize_config(config)

    return config


def cmd_show_config(args: argparse.Namespace, hook: Hook) -> None:
    config = make_config(args)
    if config.get('PROJECT_VERSION') is None and args.version_file:
        version = read_version_from_file_or_die(args.pattern_version,
                                                args.version_file,
                                                hook.normalize_version)
        config['PROJECT_VERSION'] = version
    print_config(config)


def cmd_build(args: argparse.Namespace, hook: Hook) -> None:
    if args.check_uncommited and not args.no_check:
        changes = git_uncommited_changes()
        if changes:
            raise PackagerError(f'Your repository has uncommited changes:\n{changes}\n'
                                'Please commit before packaging or use --no-check-uncommited')

    config = make_config(args)

    # read version
    project_version = config.get('PROJECT_VERSION')
    if project_version is None and args.version_file:
        project_version = read_version_from_file_or_die(args.pattern_version,
                                                        args.version_file,
                                                        hook.normalize_version)
        config['PROJECT_VERSION'] = project_version

    # check version
    if args.check_version and not args.no_check:
        last_tag = git_last_tag()
        if project_version != last_tag:
            raise PackagerError(
                'Repository head mismatch current version.\n'
                f'- PROJECT_VERSION: {project_version}\n'
                f'- tag: {last_tag}\n'
                'Ignored with --no-check-version')

    # remove old build directory
    remove_directory(args.output_build)

    # create buid directory
    for dirname in args.package_template_dir:
        create_build_directory(dirname, args.output_build, config)

    # buid package
    if args.build_package:
        shell_run(['dpkg-buildpackage', '-b', '-tc', '-us', '-uc', '-r'])

    if not args.no_clean:
        remove_directory(args.output_build)


def _cmd_sync_tag(version: str, args: argparse.Namespace, hook: Hook) -> None:
    project_path = os.getcwd()
    chdir(args.updated_repo_path)
    run_update_repo(lambda: hook.update_repo(version, project_path, args),
                    DEFAULT_UPDATED_REPO_NAME,
                    args.updated_repo_branch,
                    not args.no_pull_for_updated_repo,
                    None if args.no_commit_for_updated_repo \
                        else f'{args.application_name} updated to {version}')


def cmd_sync_tag(args: argparse.Namespace, hook: Hook) -> None:
    version = args.force_version
    if version is None:
        version = read_version_from_file_or_die(args.pattern_version,
                                                args.version_file,
                                                hook.normalize_version)
    _cmd_sync_tag(version, args, hook)


def cmd_create_tag(args: argparse.Namespace, hook: Hook) -> None:
    if not args.no_update_for_updated_repo and args.updated_repo_path is None:
        raise PackagerError(f'use -U or add {DEFAULT_UPDATED_REPO_NAME} repository parameter')

    content = args.version_file.read()
    args.version_file.close()
    extracted_version = extract_version_or_die(args.pattern_version,
                                               content,
                                               hook.normalize_version)

    new_version = args.force_version
    if new_version is None:
        new_version = extracted_version.version
        new_version = f'{version[0]}.{version[1]}.{version[2] + 1}'

    # update changelog
    if args.update_changelog:
        raise PackagerError('--update-changelog is unimplemented')
    #     project_name = config.get('PROJECT_NAME')
    #
    #     if not project_name:
    #         raise PackagerError(
    #             'Unknown PROJECT_NAME config.'
    #             'Add variable in target-file or run with --project-name or -s PROJECT_NAME=...')
    #
    #     if not project_version:
    #         raise PackagerError(
    #             'Unknown PROJECT_VERSION config.'
    #             'Add variable in target-file or run with --project-version or -s PROJECT_VERSION=...')
    #
    #     changelog = get_changelog_entry(project_name,
    #                                     project_version,
    #                                     config['MAINTAINER'],
    #                                     config['URGENCY'],
    #                                     config['UTC'])
    #     for dirname in args.package_template_dir:
    #         try:
    #             update_changelog(f'{dirname}/changelog', changelog)
    #         except FileNotFoundError:
    #             pass

    pos = extracted_version.position
    writeall(args.version_file.name,
             f'{content[:pos[0]]}{new_version}{content[pos[1]:]}')
    git_push_version(new_version)

    if not args.no_update_for_updated_repo:
        _cmd_sync_tag(new_version, args, hook)


def add_parser_cmd_get_version(subparsers,
                               cmd: Callable[[argparse.Namespace, Hook], None] = cmd_show_version
                               ) -> argparse.ArgumentParser:
    subparser = subparsers.add_parser('version', aliases=['g', 'get'],
                                      help='Get version')
    add_arguments_for_get_version_command(subparser)
    subparser.set_defaults(cmd_func=cmd)
    return subparser


def add_parser_cmd_config(subparsers,
                          cmd: Callable[[argparse.Namespace, Hook], None] = cmd_show_config
                          ) -> argparse.ArgumentParser:
    subparser = subparsers.add_parser('config', aliases=['c', 'config', 'show'],
                                      help='Show configuration')
    add_arguments_for_show_config_command(subparser)
    subparser.set_defaults(cmd_func=cmd)
    return subparser


def add_parser_cmd_build(subparsers,
                         cmd: Callable[[argparse.Namespace, Hook], None] = cmd_build
                         ) -> argparse.ArgumentParser:
    subparser = subparsers.add_parser('build', aliases=['b'],
                                      help='Build package options')
    add_arguments_for_build_command(subparser)
    subparser.set_defaults(cmd_func=cmd)
    return subparser


def add_parser_cmd_sync_tag(subparsers,
                            cmd: Callable[[argparse.Namespace, Hook], None] = cmd_sync_tag
                            ) -> argparse.ArgumentParser:
    subparser = subparsers.add_parser('sync', aliases=['s', 'u'],
                                      help='Synchronize tag with an other repository')
    add_arguments_for_sync_tag_command(subparser)
    subparser.set_defaults(cmd_func=cmd)
    return subparser


def add_parser_cmd_create_tag(subparsers,
                              cmd: Callable[[argparse.Namespace, Hook], None] = cmd_create_tag
                              ) -> argparse.ArgumentParser:
    subparser = subparsers.add_parser('create-tag', aliases=['t'],
                                      help='Create a new tag')
    add_arguments_for_create_tag_command(subparser)
    subparser.set_defaults(cmd_func=cmd)
    return subparser


def add_help_with_subparser(parser: argparse.ArgumentParser) -> List[argparse.ArgumentParser]:
    """
    add help that show subcommand with -h/--help
    """
    printable_subparsers: List[argparse.ArgumentParser] = []

    def print_help(long_format: bool):
        parser.print_help()
        print('\n\nCommands:', end='')
        for subparser in printable_subparsers:
            print('\n\n')
            if long_format:
                subparser.print_help()
            else:
                subparser.print_usage()
        parser.exit()


    class Help(argparse.Action):
        def __call__(self, parser, namespace, values, option_string = None):
            print_help(self.const)

    parser.add_argument('-h', '--help', nargs=0, action=Help,
                        help='show help message and exit')
    parser.add_argument('--help-all', nargs=0, action=Help, const=True,
                        help='show help message and exit')

    parser.set_defaults(cmd_func=lambda *args, **kargs: print_help(False))
    return printable_subparsers


def argument_parser(description: str = 'Packager for proxies repositories'
                    ) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description, add_help=False)
    printable_subparsers = add_help_with_subparser(parser)

    subparsers = parser.add_subparsers(dest='selected_cmd')
    printable_subparsers.append(add_parser_cmd_get_version(subparsers))
    printable_subparsers.append(add_parser_cmd_config(subparsers))
    printable_subparsers.append(add_parser_cmd_build(subparsers))
    printable_subparsers.append(add_parser_cmd_create_tag(subparsers))
    printable_subparsers.append(add_parser_cmd_sync_tag(subparsers))

    return parser


def run_packager(args: argparse.Namespace, hook: Hook = Hook()) -> None:
    args.cmd_func(args, hook=hook)

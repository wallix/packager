#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getopt
import sys
import shutil
import os
import re
import platform
import datetime
import argparse


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

rgx_replace_var = re.compile('%[A-Z][A-Z0-9_]*%')

def replace_dict_all(text:str, dico:dict) -> str:
    result = []
    pos = 0
    for m in rgx_replace_var.finditer(text):
        result.append(text[pos:m.start()])
        var = m.group()
        result.append(dico.get(var[1:-1], var))
        pos = m.end()
    result.append(text[pos:])
    return ''.join(result)


parser = argparse.ArgumentParser(description='Packager for proxies repositories')
parser.add_argument('target', metavar='PATH', type=str, help='target file')
parser.add_argument('--build', metavar='DIRNAME', type=str, default='debian', help='build directory')
parser.add_argument('--no-clean', action='store_true', help='do not remove existing build directory')
parser.add_argument('--package-template', metavar='DIRNAME', type=str,
                    default='packaging/template/debian', help='package template directory')
parser.add_argument('--build-package', action='store_true', help='run dpkg-buildpackage')
parser.add_argument('--project-name', metavar='NAME', type=str)
parser.add_argument('--project-version', metavar='VERSION', type=str)
parser.add_argument('--update-changelog', action='store_true')
parser.add_argument('--urgency', type=str, default='low')
parser.add_argument('--utc', type=str, default='0200')
parser.add_argument('--maintainer', type=str, default='Proxies Team <R&D-Project-Bastion-Proxies@wallix.com>')
parser.add_argument('--distribution-name')
parser.add_argument('--distribution-version')
parser.add_argument('--distribution-id')
parser.add_argument('--package-distribution')
parser.add_argument('-s', '--variable', metavar='VARIABLE=VALUE', action='append', default=[])
parser.add_argument('--show-config', action='store_true', help='show configs')

args = parser.parse_args()

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

# Parse target Config files
parse_config_rgx = re.compile('^\s*([^#][^=]*)=(.*)$')
with open(args.target) as f:
    for line in f:
        if m := re.search(parse_config_rgx, line):
            configs[m.group(1).strip()] = m.group(2).strip()

if not configs['PKG_DISTRIBUTION']:
    if configs['DIST_NAME'].lower() == 'ubuntu':
        configs['PKG_DISTRIBUTION'] = 'unstable'
    else:
        configs['PKG_DISTRIBUTION'] = configs['DIST_ID']

if not configs['TARGET_NAME']:
    if configs['DIST_NAME'].lower() == 'ubuntu':
        configs['TARGET_NAME'] = '+' + configs['DIST_ID']

configs.update(variable.partition('=')[0::2] for variable in args.variable)

if args.show_config:
    variables = []
    for k,v in configs.items():
        variables.append(f'{k} = {v}')
    print('\n'.join(variables))
    exit(0)

project_version = configs['PROJECT_VERSION']
project_name = configs['PROJECT_NAME']

if not project_version or not project_name:
    if not project_version:
        print('--project-version or -s PROJECT_VERSION=... is missing', file=sys.stderr)
    if not project_name:
        print('--project-name or -s PROJECT_NAME=... is missing', file=sys.stderr)
    print(file=sys.stderr)
    parser.print_help()
    exit(1)


if args.update_changelog:
    changelog = get_changelog_entry(project_name,
                                    project_version,
                                    configs['MAINTAINER'],
                                    configs['URGENCY'],
                                    configs['UTC'])
    changelog_path = f'{args.package_template}/changelog'
    changelog += readall(changelog_path)
    writeall(changelog_path, changelog)


try:
    shutil.rmtree(args.build)
except:
    pass

os.mkdir(args.build, 0o766)

rgx_tempfile = re.compile('^#.*#$|~$')
filenames = filter(lambda fname: rgx_tempfile.search(fname) is None,
                   os.listdir(args.package_template))

for filename in filenames:
    out = readall(f'{args.package_template}/{filename}')
    out = replace_dict_all(out, configs)
    writeall(f'{args.build}/{filename}', out)

if args.build_package:
    status = os.system('dpkg-buildpackage -b -tc -us -uc -r')
    if status:
        print('Build failed: dpkg-buildpackage error', file=sys.stderr)
        exit(2)

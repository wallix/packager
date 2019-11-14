#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getopt
import sys
import shutil
import os
import re
import platform
import datetime


def usage():
    print("Usage: %s [-h|--help] --version version [--project-name name] "
          "[--build dirname] [--build-package] [--no-entry-changelog] "
          "[--distribution-name name] [--distribution-version version] "
          "[--distribution-id id] [--arch arch] [--package-distribution name] "
          "[--package-template dirname] [--force-target target] "
          "[--urgency urgency] [--authors authors] [--utc utc]" % sys.argv[0])


try:
    options, args = getopt.getopt(sys.argv[1:], "h",
                                  ["help",
                                   "version=",
                                   "project-name=",
                                   "build=",
                                   "build-package",
                                   "no-entry-changelog",
                                   "distribution-name=",
                                   "distribution-version=",
                                   "distribution-id=",
                                   "arch=",
                                   "package-template=",
                                   "force-target=",
                                   "urgency=",
                                   "utc=",
                                   "authors="])
except getopt.GetoptError as err:
    print(str(err))
    usage()
    sys.exit(2)


class opts(object):
    packagetemp = "packaging/template/debian"
    force_target = None
    project_name = None

    build_package = False
    entry_changelog = True
    urgency = "low"
    authors = None

    dirname = "debian"
    utc = "0200"

    config = {}
    config["%PREFIX%"] = 'usr/local'
    config["%TARGET_CHANGELOG_DISTRIBUTION_NAME%"] = ''
    config["%ARCH%"] = platform.machine()
    (config["%DIST_NAME%"],
     config["%DIST_VERSION%"],
     config["%DIST_ID%"]) = platform.linux_distribution()
    force_config = {}


for o, a in options:
    if o in ("-h", "--help"):
        usage()
        sys.exit(1)
    elif o == "--build":
        opts.dirname = a
    elif o == "--version":
        opts.force_config["%VERSION%"] = a
    elif o == "--project-name":
        opts.project_name = a
    elif o == "--build-package":
        opts.build_package = True
    elif o == "--no-entry-changelog":
        opts.entry_changelog = False
    elif o == "--distribution-name":
        opts.force_config["%DIST_NAME%"] = a
    elif o == "--distribution-version":
        opts.force_config["%DIST_VERSION%"] = a
    elif o == "--distribution-id":
        opts.force_config["%DIST_ID%"] = a
    elif o == "--arch":
        opts.force_config["%ARCH%"] = a
    elif o == "--package-distribution":
        opts.force_config["%PKG_DISTRIBUTION%"] = a
    elif o == "--package-template":
        opts.packagetemp = a
    elif o == "--force-target":
        opts.force_target = a
    elif o == "--urgency":
        opts.urgency = a
    elif o == "--authors":
        opts.authors = a
    elif o == "--utc":
        opts.utc = a


if "%VERSION%" not in opts.force_config:
    print("--version is missing")
    usage()
    sys.exit(2)

if not opts.force_target:
    opts.force_target = "packaging/targets/"
    if "%DIST_NAME%" in opts.force_config:
        opts.force_target += opts.force_config["%DIST_NAME%"].lower()
    else:
        opts.force_target += opts.config["%DIST_NAME%"].lower()

# remove existing deban directory BEGIN

try:
    shutil.rmtree(opts.dirname)
except:
    pass
# remove existing deban directory END


# IO Files functions BEGIN
def readall(filename):
    with open(filename) as f:
        return f.read()


def writeall(filename, s):
    with open(filename, "w+") as f:
        f.write(s)


def copy_and_replace(src, dst, old, new):
    out = readall(src)
    out = out.replace(old, new)
    writeall(dst, out)


# Parse target Config files
rgx_general = re.compile("^([^#][^=]*)\s*=\s*(.*)$")


def parse_config_line(line):
    m = re.search(rgx_general, line.strip())
    if m:
        opts.config['%%%s%%' % m.group(1).strip()] = m.group(2).strip()


def parse_target_param(filename):
    with open(filename) as f:
        for l in f:
            parse_config_line(l)
# IO Files functions END


# Replace occurences in templates with dictionnaire
rgx_var = re.compile("(%[A-Z][A-Z0-9_]*%)")


def replace_dict_line(line, dico):
    res = line
    miter = rgx_var.finditer(res)
    for m in reversed(list(miter)):
        value = dico.get(m.group(1))
        if not value:
            value = ''
        res = res[:m.start(1)] + value + res[m.end(1):]
    return res


def replace_dict_file(filename, dico):
    res = ''
    with open(filename) as f:
        for l in f:
            res += replace_dict_line(l, dico)
    return res


def copy_and_replace_dict_file(filename, dico, target):
    out = replace_dict_file(filename, dico)
    writeall(target, out)


def get_changelog_entry(project_name, version, authors, urgency, utc):
    if 'EDITOR' not in os.environ:
        os.environ['EDITOR'] = 'nano'

    changelog = ''

    tmp_changelog = "/tmp/%s-changelog.tmp" % version
    if os.system("%s %s" % (os.environ['EDITOR'], tmp_changelog)):
        raise Exception("Error in `%s %s`" % (os.environ['EDITOR'],
                                              tmp_changelog))
    with open(tmp_changelog, "r") as f:
        for line in f:
            if line and line != "\n":
                changelog += "  * "
                changelog += line
    try:
        os.remove(tmp_changelog)
    except:
        pass

    if not changelog:
        raise Exception("Change log is empty")

    return ("%s (%s%%TARGET_NAME%%) %%PKG_DISTRIBUTION%%; "
            "urgency=%s\n\n%s\n\n -- %s  %s\n\n" % (
                project_name,
                version,
                urgency,
                changelog,
                authors,
                datetime.datetime.today().strftime(
                    "%%a, %%d %%b %%Y %%H:%%M:%%S +%s" % utc
                )
            ))


# control file for dpkg packager only allow 'amd64' for 64bits architectures
# and 'i386' for 32bits or any if there is no specification
def archi_to_control_archi(architecture):
    if architecture in ['x86_64', 'amd64']:
        return 'amd64'
    if architecture in ['i686', 'i386']:
        return 'i386'
    return architecture


status = 0

try:
    # Set debian (packaging data) directory with distro specific
    # packaging files BEGIN
    # Create temporary directory
    os.mkdir(opts.dirname, 0o766)

    # existing target parameters
    if opts.force_target:
        try:
            parse_target_param("%s" % opts.force_target)
        except IOError:
            raise Exception('Target param file not found (%s)' %
                            opts.force_target)

    if "%ARCH%" in opts.force_config:
        opts.force_config["ARCH"] = archi_to_control_archi(
            opts.force_config["ARCH"]
        )

    for k in opts.force_config:
        opts.config[k] = opts.force_config[k]

    if "%PKG_DISTRIBUTION%" not in opts.config:
        if opts.config["%DIST_NAME%"].lower() == 'ubuntu':
            opts.config["%PKG_DISTRIBUTION%"] = 'unstable'
        else:
            opts.config["%PKG_DISTRIBUTION%"] = opts.config["%DIST_ID%"]

    if "%TARGET_NAME%" not in opts.config:
        if opts.config["%DIST_NAME%"].lower() == 'ubuntu':
            opts.config["%TARGET_NAME%"] = "+" + opts.config["%DIST_ID%"]
        else:
            opts.config["%TARGET_NAME%"] = ''

    if "%PROJECT_NAME%" not in opts.config:
        opts.config["%PROJECT_NAME%"] = opts.project_name

    if not opts.config["%PROJECT_NAME%"]:
        raise Exception('Project whitout name')

    if not opts.authors:
        opts.authors = opts.config["%MAINTAINER%"] if (
            "%MAINTAINER%" in opts.config) else "Maintainer"

    # BEGIN update changelog
    changelog = ''
    if opts.entry_changelog:
        changelog = get_changelog_entry(
            opts.config["%PROJECT_NAME%"],
            opts.config["%VERSION%"],
            opts.authors,
            opts.urgency,
            opts.utc
        )

    changelog += readall("%s/changelog" % opts.packagetemp)

    if opts.entry_changelog:
        writeall("%s/changelog" % opts.packagetemp, changelog)

    writeall("%s/changelog" % opts.dirname, changelog)
    # END update changelog

    for filename in [
            "%s.preinst" % opts.config["%PROJECT_NAME%"],
            "%s.postinst" % opts.config["%PROJECT_NAME%"],
            "%s.prerm" % opts.config["%PROJECT_NAME%"],
            "%s.postrm" % opts.config["%PROJECT_NAME%"]
    ]:
        try:
            copy_and_replace_dict_file("%s/%s" % (opts.packagetemp, filename),
                                       opts.config,
                                       "%s/%s" % (opts.dirname, filename))
        except IOError as e:
            if e.errno != 2:
                raise e

    for filename in [
            "%s.install" % opts.config["%PROJECT_NAME%"],
            "changelog",
            "rules",
            "control",
            "copyright"
    ]:
        copy_and_replace_dict_file("%s/%s" % (opts.packagetemp, filename),
                                   opts.config,
                                   "%s/%s" % (opts.dirname, filename))

    for filename in [
            "compat"
    ]:
        shutil.copy("%s/%s" % (opts.packagetemp, filename), "%s/%s" %
                    (opts.dirname, filename))

    if opts.build_package:
        status = os.system("dpkg-buildpackage -b -tc -us -uc -r")
    if status:
        raise Exception("dpkg-buildpackage error.")
    exit(0)
except Exception as e:
    print("Build failed: %s" % e)
    exit(status % 255 if status else -1)

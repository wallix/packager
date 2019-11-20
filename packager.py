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
          "[--use-pybuild] [--no-clean] "
          "[--use-common-changelog] [--update-changelog] "
          "[--urgency urgency] [--authors authors] [--utc utc]" % sys.argv[0])


try:
    options, args = getopt.getopt(sys.argv[1:], "h",
                                  ["help",
                                   "version=",
                                   "project-name=",
                                   "build=",
                                   "build-package",
                                   "no-entry-changelog",
                                   "use-pybuild",
                                   "use-common-changelog",
                                   "no-clean",
                                   "update-changelog",
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
    target_path = "packaging/targets/"
    force_target = None
    project_name = None

    build_package = False
    entry_changelog = True
    use_common_changelog = False
    common_changelog_path = "packaging/template/"
    common_changelog_file = "common_changelog"
    urgency = "low"
    authors = None

    dirname = "debian"
    utc = "0200"

    use_pybuild = False
    clean = True
    update_changelog = False

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
        opts.force_config["%PROJECT_NAME%"] = a
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
    elif o == "--package-template" and not opts.use_pybuild:
        opts.packagetemp = a
    elif o == "--force-target" and not opts.use_pybuild:
        opts.force_target = a
    elif o == "--urgency":
        opts.urgency = a
    elif o == "--authors":
        opts.authors = a
    elif o == "--utc":
        opts.utc = a
    elif o == "--no-clean":
        opts.clean = False
    elif o == "--use-common-changelog":
        opts.use_common_changelog = True
    elif o == "--update-changelog":
        opts.update_changelog = True
    elif o == "--use-pybuild":
        # force pybuild templates and targets
        opts.use_pybuild = True
        opts.packagetemp = "packaging/template/pybuild/"
        opts.target_path = "packaging/targets/pybuild/"


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


def update_changelog_template(project_name, version):
    if not opts.entry_changelog:
        return False
    changelog = ''
    common_changelog = os.path.join(opts.common_changelog_path,
                                    opts.common_changelog_file)
    if opts.entry_changelog and opts.use_common_changelog:
        changelog = get_changelog_entry(
            project_name,
            version,
            opts.authors,
            opts.urgency,
            opts.utc
        )
        changelog += readall(common_changelog)
        writeall(common_changelog, changelog)
    elif opts.entry_changelog:
        changelog = get_changelog_entry(
            project_name,
            version,
            opts.authors,
            opts.urgency,
            opts.utc
        )
        changelog += readall("%s/changelog" % opts.packagetemp)
        writeall("%s/changelog" % opts.packagetemp, changelog)


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


if "%VERSION%" not in opts.force_config:
    print("--version is missing")
    usage()
    sys.exit(2)


try:
    if ("%PROJECT_NAME%" in opts.force_config
        and "%VERSION%" in opts.force_config
        and opts.update_changelog):
        update_changelog_template(opts.force_config["%PROJECT_NAME%"],
                                  opts.force_config["%VERSION%"])
        opts.entry_changelog = False  # no need to update changelog again
        if not opts.build_package:
            exit(0)
except Exception as e:
    print("Update changelog failed: %s" % e)
    exit(-1)

if not opts.force_target:
    opts.force_target = opts.target_path
    if "%DIST_NAME%" in opts.force_config:
        opts.force_target += opts.force_config["%DIST_NAME%"].lower()
    else:
        opts.force_target += opts.config["%DIST_NAME%"].lower()


# remove existing build directory BEGIN
def remove_build_dir():
    try:
        shutil.rmtree(opts.dirname)
    except:
        pass
# remove existing build directory END


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


# control file for dpkg packager only allow 'amd64' for 64bits architectures
# and 'i386' for 32bits or any if there is no specification
def archi_to_control_archi(architecture):
    if architecture in ['x86_64', 'amd64']:
        return 'amd64'
    if architecture in ['i686', 'i386']:
        return 'i386'
    return architecture


PYTHON_VERSION_2 = '2'
PYTHON_VERSION_3 = '3'

PYBUILD_MAPPING = {
    PYTHON_VERSION_2: 'python',
    PYTHON_VERSION_3: 'python3',
}


PYVERSION_MAPPING = {
    PYTHON_VERSION_2: '%PYTHON_VERSION_2%',
    PYTHON_VERSION_3: '%PYTHON_VERSION_3%',
}


def pybuild_parameters():
    pybuilds = opts.config.get("%PYBUILD%", '').split(',')
    pybuilds = [ver for ver in pybuilds if ver in PYBUILD_MAPPING]
    if not pybuilds:
        return {}
    # create config param for each version of python
    configs_params = {
        py_ver: dict(opts.config) for py_ver in pybuilds
    }
    for py_ver in configs_params:
        configs_params[py_ver]["%PYTHON_VERSION_NUM%"] = (
            opts.config.get(PYVERSION_MAPPING[py_ver])
        )
    return configs_params


def generate_service_files(filename, pybuilds_params):
    if filename == opts.common_changelog_file:
        filename = "changelog"
    dest_filenames = [(filename, opts.config)]
    if not pybuilds_params:
        return dest_filenames

    if filename.endswith(".service"):
        dest_filenames = [
            ("%s-%s.%s" % (PYBUILD_MAPPING[py_ver],
                           opts.config["%PROJECT_NAME%"],
                           filename),
             pybuilds_params[py_ver])
            for py_ver in pybuilds_params
        ]
    elif filename.startswith("%s." % opts.config["%PROJECT_NAME%"]):
        dest_filenames = [
            ("%s-%s" % (PYBUILD_MAPPING[py_ver], filename),
             pybuilds_params[py_ver])
            for py_ver in pybuilds_params
        ]
    return dest_filenames


rgx_tempfile = re.compile("^#.*#$|~$")


def temp_filename(filename):
    return rgx_tempfile.search(filename) is not None


status = 0

try:
    remove_build_dir()
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

    if opts.entry_changelog:
        update_changelog_template(opts.config["%PROJECT_NAME%"],
                                  opts.config["%VERSION%"])

    add_changelog = None
    common_changelog = os.path.join(opts.common_changelog_path,
                                    opts.common_changelog_file)
    if opts.use_common_changelog and os.path.isfile(common_changelog):
        add_changelog = (opts.common_changelog_path,
                         opts.common_changelog_file)

    excluded_files = set()
    if add_changelog is not None:
        excluded_files.add('changelog')

    fileslist = [
        (opts.packagetemp, fn)
        for fn in os.listdir(opts.packagetemp)
        if (not temp_filename(fn) and fn not in excluded_files)
    ]
    if add_changelog is not None:
        fileslist.append(add_changelog)

    pybuilds_params = pybuild_parameters()
    for (path, filename) in fileslist:
        dest_filenames = generate_service_files(filename, pybuilds_params)
        for dest_filename, config_param in dest_filenames:
            copy_and_replace_dict_file(
                "%s/%s" % (path, filename),
                config_param or opts.config,
                "%s/%s" % (opts.dirname, dest_filename)
            )
    if opts.build_package:
        status = os.system("dpkg-buildpackage -b -tc -us -uc -r")
    if status:
        raise Exception("dpkg-buildpackage error.")
    if opts.clean:
        remove_build_dir()
    exit(0)
except Exception as e:
    print("Build failed: %s" % e)
    if opts.clean:
        remove_build_dir()
    exit(status % 255 if status else -1)

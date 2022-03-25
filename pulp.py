#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##
# Copyright (c) 2010-2022 WALLIX, SARL. All rights reserved.
# Licensed computer software. Property of WALLIX.
# Product name: Packager
# Author(s): Jonathan Poelen
# Module description: Synchronize public submodule
##

import sys
import re
from wallix_packager.synchronizer import (run_synchronizer,
                                          argument_parser,
                                          read_gitconfig)

remove_prefix = re.compile('^modules/')
gitconfig = read_gitconfig()
parser = argument_parser(gitconfig, 'Synchronize submodules')
args = parser.parse_intermixed_args()
submodule_path = args.submodule[-1]

try:
    run_synchronizer(gitconfig, submodule_path, args)
except Exception as e:
    from .wallix_packager.error import print_error
    print_error(e, f'Setting {submodule_path} submodule failed: ')
    sys.exit(1)

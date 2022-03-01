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
from wallix_packager.synchronizer import run_synchronizer, argument_parser

parser = argument_parser('Synchronize submodules')
args = parser.parse_args()
submodule_path = args.submodule[-1]

try:
    run_synchronizer(submodule_path, args)
except Exception as e:
    from .wallix_packager.error import print_error
    print_error(e, f'Setting {submodule_path} submodule failed: ')
    sys.exit(1)

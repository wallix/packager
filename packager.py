#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##
# Copyright (c) 2010-2022 WALLIX, SARL. All rights reserved.
# Licensed computer software. Property of WALLIX.
# Product name: Packager
# Author(s): Jonathan Poelen
# Module description: Create package and git tag
##

from wallix_packager.packager import run_packager, argument_parser


parser = argument_parser('Packager for proxies repositories (v2.0.0)')
args = parser.parse_args()
try:
    run_packager(args)
except Exception as e:
    from .wallix_packager.error import print_error
    print_error(e)
    exit(1)

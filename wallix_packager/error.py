#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##
# Copyright (c) 2010-2022 WALLIX, SARL. All rights reserved.
# Licensed computer software. Property of WALLIX.
# Product name: Packager
# Author(s): Jonathan Poelen
##

import sys
import traceback


def print_error(exception: Exception, prefix: str = '', file=sys.stderr) -> None:
    s = str(exception)
    border = '=' * (len(s) + len(prefix) + 4)
    print(f'\x1b[31m{border}\n= {prefix}{s} =\n{border}\x1b[0m', file=file)
    traceback.print_tb(sys.exc_info()[2], file=file)

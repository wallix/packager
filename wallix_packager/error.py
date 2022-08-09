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
from typing import Union


def print_error(s: Union[str, Exception], file=sys.stderr) -> None:
    parts = str(s).split('\n')
    line_size = max(map(len, parts))
    border = '=' * (line_size + 4)
    s = ''.join(f'| {s}{" " * (line_size - len(s))} |\n' for s in parts)
    print(f'\x1b[31m{border}\n{s}{border}\x1b[0m', file=file)
    traceback.print_tb(sys.exc_info()[2], file=file)

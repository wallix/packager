#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##
# Copyright (c) 2010-2022 WALLIX, SARL. All rights reserved.
# Licensed computer software. Property of WALLIX.
# Product name: Packager
# Author(s): Jonathan Poelen
##

import re
from typing import Tuple

TypingVersion = Tuple[int, int, int, int, int, str]


def get_version_extractor() -> re.Pattern:
    return re.compile(
        r'[^\d]*(\d+)(?:\.(\d+))?(?:[-.](\d+))?(?:[-.](\d+))?(?:[-.](\d+))?(.*)')


def re_match_version_to_tuple(m: re.Match) -> TypingVersion:
    return (
        int(m.group(1)),
        int(m.group(2) or 0),
        int(m.group(3) or 0),
        int(m.group(4) or 0),
        int(m.group(5) or 0),
        m.group(6)
    )


def less_version(lhs_version: str, rhs_version: str) -> bool:
    patt = get_version_extractor()
    m1 = patt.match(lhs_version)
    m2 = patt.match(rhs_version)
    return re_match_version_to_tuple(m1) < re_match_version_to_tuple(m2)

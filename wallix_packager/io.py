#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##
# Copyright (c) 2010-2022 WALLIX, SARL. All rights reserved.
# Licensed computer software. Property of WALLIX.
# Product name: Packager
# Author(s): Jonathan Poelen
##

def readall(filename: str, encoding: str = 'utf-8') -> str:
    with open(filename, encoding=encoding) as f:
        return f.read()


def writeall(filename: str, s: str, encoding: str = 'utf-8') -> None:
    with open(filename, 'w+', encoding=encoding) as f:
        f.write(s)

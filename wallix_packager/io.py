#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##
# Copyright (c) 2010-2022 WALLIX, SARL. All rights reserved.
# Licensed computer software. Property of WALLIX.
# Product name: Packager
# Author(s): Jonathan Poelen
##

def readall(filename: str) -> str:
    with open(filename) as f:
        return f.read()


def writeall(filename: str, s: str) -> None:
    with open(filename, 'w+') as f:
        f.write(s)

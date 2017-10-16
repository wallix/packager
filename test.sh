#!/bin/bash

# ./test.sh --push --update-version 1.2 -- --distribution-name wab

cd "$(dirname "$0")"

version_file=VERSION

PREFIX_VERSION='/^version=/!d;s/^version='

get_version () { sed -E "$PREFIX_VERSION(.*)$/\1/" -- "$version_file"; }
set_version () { sed -E "$PREFIX_VERSION.*/version=$1/" -i -- "$version_file"; }

PACKAGER_PATH=./packager.py
source tagger.sh

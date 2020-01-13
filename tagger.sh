#!/bin/bash

# require get_version and set_version functions
# optional PACKAGER_PATH

packager=${PACKAGER_PATH:-modules/packager/packager.py}

have_get_set_version=1
for func in set_version get_version ; do
    if ! type -t $func >/dev/null ; then
        echo [dev error] missing $func function >&2
        have_get_set_version=0
    fi
done

[ $have_get_set_version -eq 0 ] && exit 42

current_version=$(get_version) || exit $?
progname="$0"

usage ()
{
    echo 'usage:' >&2
    echo "  $progname -u,--update-version new-version [-f,--force-version] [-p,--push] [-- packager_args...]" >&2
    echo "  $progname -g,--get-version" >&2
    echo "current version: $current_version"
    exit 1
}

TEMP=`getopt -o 'gpfu:' -l 'get-version,push,force-version,update-version:' -- "$@"`

if [ $? != 0 ] ; then usage >&2 ; fi

eval set -- "$TEMP"

new_version=
gver=0
push=0
commitandtag=1
force_vers=0
while true; do
  case "$1" in
    -g|--get-version) gver=1; shift ;;
    -p|--push) push=1; shift ;;
    -f|--force-version) force_vers=1; shift ;;
    -c|--no-commit-and-tag) commitandtag=0; shift ;;
    -u|--update-version)
        [ -z "$2" ] && usage
        new_version="$2"
        shift 2
        ;;
    --) shift; break ;;
    * ) usage; exit 1 ;;
  esac
done


if [ $gver = 1 ] ; then
    echo "$current_version"
    exit
fi


if [ -z "$new_version" ] ; then
    echo missing --new-version
    usage
fi

greater_version ()
{
    [ "$current_version" != "$new_version" ] && {
        local t=$(echo -e "$current_version\n$new_version")
        [ "$(echo "$t" | sort -V)" = "$t" ]
    }
}

if [ $force_vers -eq 0 ] && ! greater_version "$new_version" "$current_version"  ; then
    echo version "$current_version" is less than or equal to "$new_version"
    exit 1
fi

gdiff=$(GIT_PAGER=cat git diff --shortstat)

if [ $? != 0 ] || [ "$gdiff" != '' ] ; then
    echo -e "your repository has uncommited changes:\n$gdiff\nPlease commit before packaging." >&2
    exit 2
fi

check_tag ()
{
    grep -m1 -o "^$new_version$" && {
        echo "tag $new_version already exists ("$1")."
        exit 2
    }
    return 0
}

echo "Check tag"

git tag --list | check_tag locale || exit $?
git ls-remote --tags origin | sed 's#.*/##' | check_tag remote || exit $?


set -e

echo "Update version"

set_version "$new_version"

$packager --version "$new_version" --update-changelog "$@"
if [ $commitandtag = 1 ] ; then
    git commit -am "Version $new_version"
    git tag "$new_version"
fi
if [ $push = 1 ] ; then
    git push && git push --tags
fi

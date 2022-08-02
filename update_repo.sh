#!/bin/bash

set -e

PROJECT_NAME=${PROJECT_NAME:-$(dirname "$0")}
UPDATED_PROJECT_NAME=${UPDATED_PROJECT_NAME:-updated}
PROJECT_BRANCH=${PROJECT_BRANCH:-master}
DEFAULT_UPDATED_PROJECT_BRANCH=${DEFAULT_UPDATED_PROJECT_BRANCH:-master}

if [[ "$(type -t update_repo)" != 'function' ]]; then
    echo "Missing update_repo function" >&2
    exit 1
fi

# check branch
current_branch=$(git symbolic-ref HEAD)
current_branch="${current_branch#refs/heads/}"
if [[ "$current_branch" != "$PROJECT_BRANCH" ]] ; then
  echo "$PROJECT_NAME '$current_branch' branch is not '$PROJECT_BRANCH'"
  exit 2
fi


progname=$0

usage()
{
  echo "$progname [options]  ${UPDATED_PROJECT_NAME}_path  [branch=$DEFAULT_UPDATED_PROJECT_BRANCH]
$EXTRA_USAGE_DESCRIPTION
  -c --no-checkout (implies -p)
  -p --no-pull
  -n --no-commit" >&2
  (( $# == 1 )) && exit $1
  exit 1
}

yesno()
{
    read -p "$1 [y/n] " -rn1
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

TEMP=`getopt -o 'npch'"$EXTRA_GETOPT_SHORT" -l 'no-commit,no-checkout,no-pull,help'"$EXTRA_GETOPT_LONG" -- "$@"` || usage

eval set -- "$TEMP"

if [[ "$(type -t parse_extra_getopt)" != 'function' ]]; then
    parse_extra_getopt()
    {
        usage 1
    }
fi

declare -i nocommit=0
declare -i checkout=1
declare -i pull=1
while : ; do
  case "$1" in
    -h|--help) usage 0 ;;
    -n|--no-commit) nocommit=1 ; shift ;;
    -c|--no-checkout) checkout=0 ; pull=0 ; shift ;;
    -p|--no-pull) pull=0 ; shift ;;
    --) shift ; break ;;
    * ) parse_extra_getopt "$1" ;;
  esac
done

if [[ "$(type -t post_parse_getopt)" == 'function' ]]; then
    post_parse_getopt
fi

UPDATED_PROJECT_PATH="$1"
UPDATED_PROJECT_BRANCH="$2"

if (( $checkout == 1 )); then
  if (( $# != 2 )); then
    (( $# != 1 )) && usage
    if ! yesno "Use '$DEFAULT_UPDATED_PROJECT_BRANCH' branch for '$UPDATED_PROJECT_PATH' ?"; then
        usage
    fi
    UPDATED_PROJECT_BRANCH="$DEFAULT_UPDATED_PROJECT_BRANCH"
  fi
else
  (( $# != 1 )) && usage
fi

gitecho()
{
  echo "> git $@"
  git "$@"
}

# update repo
echo "$UPDATED_PROJECT_PATH"
cd "$UPDATED_PROJECT_PATH"
gitecho fetch --tags --all -a
if (( $checkout == 1 )); then
  gitecho checkout "$UPDATED_PROJECT_BRANCH"
fi
if (( $pull == 1 )); then
  gitecho pull origin "$UPDATED_PROJECT_BRANCH" --rebase
fi
cd -


VERSION=$(git describe --tags | sed -E 's/([^-]+).*/\1/') # 1.0.132-1-gb36cc707 -> 1.0.132
cd "$UPDATED_PROJECT_PATH"

update_repo "$VERSION"
echo "${UPDATED_PROJECT_NAME}: git status before git commit -a"
gitecho status -s

if yesno "git diff ?"; then
  gitecho diff
fi

if (( $nocommit != 1 )); then
  gitecho commit -am "$PROJECT_NAME updated to $VERSION"

  if yesno "'git push origin "$UPDATED_PROJECT_BRANCH"' on '$UPDATED_PROJECT_PATH' ? [y/n] "; then
    git push origin "$UPDATED_PROJECT_BRANCH"
  fi
fi

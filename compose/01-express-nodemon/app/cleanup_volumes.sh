#! /bin/bash

set -eou pipefail

#usage: sudo ./docker-cleanup-volumes.sh [--dry-run]

docker_bin="$(which docker.io 2> /dev/null || which docker 2> /dev/null)"

# Default dir
dockerdir=/var/lib/docker

# Look for an alternate docker directory with -g/--graph option
dockerpid=$(ps ax | grep "$docker_bin" | grep -v grep | awk '{print $1; exit}') || :
if [[ -n "$dockerpid" && $dockerpid -gt 0 ]]; then
    next_arg_is_dockerdir=false
    while read -d $'\0' arg
    do
        if [[ $arg =~ ^--graph=(.+) ]]; then
            dockerdir=${BASH_REMATCH[1]}
            break
        elif [ $arg = '-g' ]; then
            next_arg_is_dockerdir=true
        elif [ $next_arg_is_dockerdir = true ]; then
            dockerdir=$arg
            break
        fi
    done < /proc/$dockerpid/cmdline
fi

dockerdir=$(readlink -f "$dockerdir")

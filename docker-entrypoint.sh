#!/usr/bin/env bash

if [ "$1" == "manage" ]; then
  shift 1
  etesync-dav-manage "$@"
  exit 0
fi

exec etesync-dav "$@"

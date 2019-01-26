#!/usr/bin/env bash

if [ "$1" == "manage" ]; then
  shift 1
  etesync-dav-manage "$@"
  exit 0
fi

echo "Upgrading etesync-dav if necessary"
pip install --upgrade etesync-dav scrypt

echo "Running etesync-dav"
exec etesync-dav "$@"

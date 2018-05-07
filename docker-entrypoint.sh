#!/usr/bin/env bash

if [ "$1" == "setup" ]; then
  read -p "Please enter the EteSync username: " USERNAME
  etesync-dav-manage add ${USERNAME}
  exit 0
fi

echo "Running etesync-dav"
etesync-dav

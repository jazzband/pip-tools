#!/bin/sh
set -e
echo "===> Running unit tests"
python -m unittest discover -s tests/unit
echo
echo "===> Running cram tests"
cram tests/*.t

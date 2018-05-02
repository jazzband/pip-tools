#!/usr/bin/env python
import os
import sys

DIR = os.path.dirname(sys.argv[1])
if not os.path.exists(DIR):
    os.makedirs(DIR)

open(
    sys.argv[1], 'wt',
).write(
    "\n".join(sys.argv[2:])
)

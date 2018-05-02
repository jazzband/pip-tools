#!/usr/bin/env python
import sys

try:
    module = __import__(sys.argv[1])
except ImportError as err:
    print("OK: {}".format(err))
else:
    raise SystemExit("FAIL: {}".format(module))

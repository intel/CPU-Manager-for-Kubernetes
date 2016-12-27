#!/usr/bin/env python


"""kcm.

Usage:
  kcm (-h | --help)
  kcm --version
  kcm (discover | describe | reconcile) [--conf-dir=<dir>]
  kcm isolate [--conf-dir=<dir>] --pool=<pool> <command> [-- <args> ...]

Options:
  -h --help         Show this screen.
  --version         Show version.
  --conf-dir=<dir>  KCM configuration directory [default: /etc/kcm].
  --pool=<pool>     Pool name: either INFRA, CONTROLPLANE or DATAPLANE.
"""
from intel import config
from docopt import docopt
import json


def main():
    args = docopt(__doc__, version="KCM 0.1.0")
    if args["describe"]:
        describe(args["--conf-dir"])
        return


def describe(conf_dir):
    c = config.Config(conf_dir)
    with c.lock():
        print(json.dumps(c.as_dict(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()

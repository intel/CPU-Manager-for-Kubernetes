#!/usr/bin/env python


"""kcm.

Usage:
  kcm (-h | --help)
  kcm --version
  kcm (init | describe | reconcile) [--conf-dir=<dir>]
  kcm isolate [--conf-dir=<dir>] --pool=<pool> <command> [-- <args> ...]

Options:
  -h --help         Show this screen.
  --version         Show version.
  --conf-dir=<dir>  KCM configuration directory [default: /etc/kcm].
  --pool=<pool>     Pool name: either infra, controlplane or dataplane.
"""
from intel import config, util
from docopt import docopt
import json


def main():
    args = docopt(__doc__, version="KCM 0.1.0")
    if args["init"]:
        init(args["--conf-dir"])
        return
    if args["describe"]:
        describe(args["--conf-dir"])
        return


def init(conf_dir):
    util.check_hugepages()


def describe(conf_dir):
    c = config.Config(conf_dir)
    with c.lock():
        print(json.dumps(c.as_dict(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()

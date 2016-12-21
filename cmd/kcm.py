#!/usr/bin/env python

"""kcm.

Usage:
  kcm (-h | --help)
  kvm --version
  kcm (discover | describe | reconcile) [--conf-dir=<dir>]
  kcm isolate [--conf-dir=<dir>] --pool=<pool> <command> [-- <args> ...]

Options:
  -h --help         Show this screen.
  --version         Show version.
  --conf-dir=<dir>  KCM configuration directory [default: /etc/kcm].
  --pool=<pool>     Pool name: either INFRA, CONTROLPLANE or DATAPLANE.
"""
from docopt import docopt


def main():
    args = docopt(__doc__, version='KCM 0.1.0')
    print("Hello KCM")
    print(args)


if __name__ == "__main__":
    main()

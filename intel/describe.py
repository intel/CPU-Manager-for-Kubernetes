from . import config
import json


def describe(conf_dir):
    c = config.Config(conf_dir)
    with c.lock():
        print(json.dumps(c.as_dict(), sort_keys=True, indent=2))

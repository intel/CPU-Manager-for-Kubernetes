from intel import util
import os
import random
import string
import subprocess
import copy


# Returns the absolute path to the test config directory with the supplied
# name.
def conf_dir(name):
    return os.path.join(util.kcm_root(), "tests", "data", "config", name)


def rand_str(length=8, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for c in range(length))


# Returns resulting stdout buffer from interpreting the supplied command with
# a shell. Raises process errors if the command exits nonzero.
def execute(cmd, args=[], env={}):
    cmd_str = "{} {}".format(cmd, " ".join(args))

    host_env = copy.deepcopy(os.environ)
    host_env.update(env)

    stdout = subprocess.check_output(cmd_str, shell=True, env=host_env)
    return stdout

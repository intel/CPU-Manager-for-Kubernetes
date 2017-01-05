from intel import util
import os
import subprocess
import copy


# Returns the absolute path to the top-level kcm script.
def kcm():
    return os.path.join(util.kcm_root(), "kcm.py")


# Returns resulting stdout buffer from interpreting the supplied command with
# a shell. Raises process errors if the command exits nonzero.
def execute(cmd, args, env=None):
    cmd_str = "{} {}".format(cmd, " ".join(args))

    host_env = copy.deepcopy(os.environ)
    if env is not None:
        host_env.update(env)

    stdout = subprocess.check_output(cmd_str, shell=True, env=host_env)
    return stdout

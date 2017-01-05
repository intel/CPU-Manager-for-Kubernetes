from intel import util
import os
import random
import string


# Returns the absolute path to the test config directory with the supplied
# name.
def conf_dir(name):
    return os.path.join(util.kcm_root(), "tests", "data", "config", name)


def rand_str(length=8, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for c in range(length))

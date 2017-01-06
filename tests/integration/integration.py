from intel import util
import os


# Returns the absolute path to the top-level kcm script.
def kcm():
    return os.path.join(util.kcm_root(), "kcm.py")

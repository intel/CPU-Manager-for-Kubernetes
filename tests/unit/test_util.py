import os
from intel import util


def test_kcm_root():
    result = util.kcm_root()
    assert os.path.isdir(os.path.join(result, "tests", "data"))

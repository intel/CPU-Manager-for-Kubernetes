from .. import helpers
from intel import discover
import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock


def test_discover_no_dp():
    temp_dir = tempfile.mkdtemp()
    conf_dir = os.path.join(temp_dir, "discover")

    helpers.execute(
        "cp",
        ["-r",
         helpers.conf_dir("ok"),
         "{}".format(conf_dir)]
    )
    helpers.execute(
        "rm",
        ["-r",
         "{}".format(os.path.join(conf_dir, "pools", "dataplane"))]
    )

    with patch('intel.discover.patch_k8s_node', MagicMock()):
        with pytest.raises(KeyError) as err:
            discover.discover(conf_dir)
        expected_msg = "Dataplane pool does not exist"
        assert err.value.args[0] == expected_msg


def test_discover_no_cldp():
    temp_dir = tempfile.mkdtemp()
    conf_dir = os.path.join(temp_dir, "discover")

    helpers.execute(
        "cp",
        ["-r",
         helpers.conf_dir("ok"),
         "{}".format(conf_dir)]
    )
    helpers.execute(
        "rm",
        ["-r",
         "{}".format(os.path.join(conf_dir, "pools",
                                  "dataplane", "*"))]
    )

    with patch('intel.discover.patch_k8s_node', MagicMock()):
        with pytest.raises(KeyError) as err:
            discover.discover(conf_dir)
        expected_msg = "No CPU list in dataplane pool"
        assert err.value.args[0] == expected_msg

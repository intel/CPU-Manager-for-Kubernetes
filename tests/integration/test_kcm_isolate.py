from .. import helpers
from . import integration
from intel import config
import os
import psutil
import subprocess
import tempfile


def test_kcm_isolate_shared():
    args = ["isolate",
            "--conf-dir={}".format(helpers.conf_dir("minimal")),
            "--pool=shared",
            "echo",
            "--",
            "foo"]
    assert integration.execute(integration.kcm(), args) == b"foo\n"


def test_kcm_isolate_exclusive():
    args = ["isolate",
            "--conf-dir={}".format(helpers.conf_dir("minimal")),
            "--pool=exclusive",
            "echo",
            "--",
            "foo"]
    assert integration.execute(integration.kcm(), args) == b"foo\n"


def test_kcm_isolate_pid_bookkeeping():
    temp_dir = tempfile.mkdtemp()
    conf_dir = os.path.join(temp_dir, "isolate")
    integration.execute(
        "cp",
        ["-r",
         helpers.conf_dir("minimal"),
         "{}".format(conf_dir)]
    )
    c = config.Config(conf_dir)

    fifo = helpers.rand_str()
    integration.execute("mkfifo", [fifo])

    p = subprocess.Popen([
            integration.kcm(),
            "isolate",
            "--conf-dir={}".format(conf_dir),
            "--pool=shared",
            "echo 1 > {} && cat {}".format(fifo, fifo)
        ])
    kcm = psutil.Process(p.pid)
    # Wait for subprocess to exist
    integration.execute("cat {}".format(fifo))
    clist = c.pools()["shared"].cpu_lists()["0"]
    assert kcm.pid in clist.tasks()
    # Signal subprocess to exit
    integration.execute("echo 1 > {}".format(fifo))
    # Wait for kcm process to terminate
    kcm.wait()
    assert kcm.pid not in clist.tasks()
    integration.execute("rm {}".format(fifo))

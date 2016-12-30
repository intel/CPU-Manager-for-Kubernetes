from . import integration
from intel import config
import os
import psutil
import subprocess
import tempfile


def test_kcm_isolate_shared():
    args = ["isolate",
            "--conf-dir={}".format(integration.conf_dir("minimal")),
            "--pool=shared",
            "echo",
            "--",
            "foo"]
    assert integration.execute(integration.kcm(), args) == b"foo\n"


def test_kcm_isolate_exclusive():
    args = ["isolate",
            "--conf-dir={}".format(integration.conf_dir("minimal")),
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
         integration.conf_dir("minimal"),
         "{}".format(conf_dir)]
    )
    c = config.Config(conf_dir)

    p = subprocess.Popen([
            integration.kcm(),
            "isolate",
            "--conf-dir={}".format(conf_dir),
            "--pool=shared",
            "echo",
            "--",
            "sleep",
            "300"  # 5 minutes
        ])
    kcm = psutil.Process(p.pid)
    # Wait for child (sleep) process to exist
    while len(kcm.children()) == 0:
        continue  # busy-waiting...
    children = kcm.children()
    assert len(children) == 1
    sleep = children[0]
    clist = c.pools()["shared"].cpu_lists()["0"]
    assert kcm.pid in clist.tasks()
    sleep.kill()
    # Wait for kcm process to terminate
    kcm.wait()
    assert kcm.pid not in clist.tasks()

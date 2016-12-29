from . import integration


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

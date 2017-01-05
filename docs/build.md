# Building `kcm`

## System requirements

 - Docker 1.12.1 or above
 - Python 3.4.4 or above

A running docker daemon (with permissions for the current user to issue docker
commands) is required before running:

```bash
$ make
```

After this step completes successfully, `kcm` can be run inside a Docker
container:

```bash
$ docker run -it kcm ...
```

Before running any subsequent comments, the KCM configuration directory must
exist. Note that is it important that this configuration directory is
bind-mounted into the container, such that the directory resides on the host
system and _not_ in the container.

Configuration directory initialization is done through
[`kcm init`][doc-init]:

```bash
$ kcm init
```

Please note that the default settings require at least six physical cores
(four for data plane, one for control plane and one for infra).
To change these settings, use the `--num-dp-cores` and `--num-cp-cores` flags.

[doc-init]: cli.md#kcm-init

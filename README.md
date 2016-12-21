# kubernetes-comms-mvp

## Usage
**TODO**

## Configuration

_Example KCM pool filesystem configuration format:_

```
etc
└── kcm
    ├── lock
    └── pools
        ├── controlplane
        │   ├── 3,11
        │   │   └── tasks
        │   └── exclusive
        ├── dataplane
        │   ├── 4,12
        │   │   └── tasks
        │   ├── 5,13
        │   │   └── tasks
        │   ├── 6,14
        │   │   └── tasks
        │   ├── 7,15
        │   │   └── tasks
        │   └── exclusive
        └── infra
            ├── 0-2,8-10
            │   └── tasks
            └── exclusive
```

_wherein:_

- `/etc/kcm/lock` is a lock file to protect against conflicting
  concurrent modification
- `/etc/kcm/pools/<pool>/exclusive` determines whether each cpuset in
  the pool can be shared (value 0) or not (value 1).
- `/etc/kcm/pools/<pool>/<cpulist>/tasks` contains the Linux process IDs
  of containers to which the CPUset has been allocated.

import subprocess


def stdout_matches(cmd, args, expected):
    cmd_str = "{} {}".format(cmd, " ".join(args))
    stdout = subprocess.check_output(cmd_str, shell=True)
    return stdout == expected

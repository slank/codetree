import subprocess
import shutil
import os
from contextlib import contextmanager


class FileManipulationError(Exception):
    pass


@contextmanager
def cd(dest):
    here = os.getcwd()
    os.chdir(dest)
    yield
    os.chdir(here)


def copy(source, dest):
    rsync(source, dest, delete=False)


def rsync(source, dest, delete=True, perms=True, links=True, times=False):
    args = "-"
    if os.path.isdir(source):
        if not source.endswith("/"):
            # The contents of source are always copied into a folder
            # with the name of dest
            source = source + "/"
        args += "r"
        if delete:
            args += "d"
    elif not os.path.isfile(source):
        raise FileManipulationError("Only files and directories can be copied")

    if perms:
        args += "p"
    if links:
        args += "l"
    if times:
        args += "t"

    cmd = ("rsync", args, source, dest)
    try:
        subprocess.check_output(cmd)
    except subprocess.CalledProcessError as e:
        raise FileManipulationError(e.message)


def link(source, dest=None, symbolic=True):
    if not dest:
        source_name = os.path.basename(source)
        current_dir = os.getcwd()
        dest = os.path.join(current_dir, source_name)
    if os.path.exists(dest):
        raise FileManipulationError("Destination already exists: {}".format(dest))

    if symbolic:
        mklink = os.symlink
    else:
        mklink = os.link

    try:
        if os.path.isabs(dest):
            mklink(source, dest)
        else:
            with cd(os.path.dirname(dest)):
                mklink(source, os.path.basename(dest))
    except OSError as e:
        raise FileManipulationError(e.message)


def mkdir(dirname, overwrite=False):
    if os.path.exists(dirname):
        if overwrite:
            shutil.rmtree(dirname)
        else:
            raise FileManipulationError("Creation of directory would overwrite existing {}".format(dirname))
    os.makedirs(dirname)

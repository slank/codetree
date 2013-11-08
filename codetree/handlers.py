from __future__ import print_function
from urlparse import urlparse
import shutil
from subprocess import (
    Popen,
    PIPE,
    STDOUT,
    check_output,
    CalledProcessError,
    check_call,
)
import os
import logging
import urllib2

import fileutils


class CommandFailure(Exception):
    def __init__(self, message, original_exception):
        self.message = message
        self.original_exception = original_exception

class NotABranch(Exception):
        pass

class NotSameBranch(Exception):
    pass

def log_failure(cmd, message, fatal=False):
    try:
        logging.info(message)
        check_output(cmd, stderr=STDOUT)
        return True
    except CalledProcessError as e:
        logging.error(e.output)
        if fatal:
            raise CommandFailure(e.output, e)
        else:
            return False
    except OSError as e:
        logging.error(e.message)
        if fatal:
            raise CommandFailure(e.message, e)
        else:
            return False


def strip_trailing_slash(value):
    if value[-1] == "/":
        return value[:-1]
    return value


class SourceHandler(object):
    schemes = tuple()

    def __init__(self, source):
        self.source = source


class BzrSourceHandler(SourceHandler):
    """Check out a bazaar working tree"""

    schemes = (
        "bzr",
        "bzr+ssh",
        "lp",
        "bzr+http",
        "bzr+https",
    )

    def __init__(self, source):
        super(BzrSourceHandler, self).__init__(source)
        scheme = urlparse(source).scheme
        if scheme in ("bzr+http", "bzr+https"):
            self.source = source[4:]
        else:
            self.source = source

    def checkout_branch(self, dest):
        parent_dir = os.path.dirname(dest)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        cmd = ('bzr', 'branch', self.source, dest)
        return log_failure(cmd, "Branching {} to {}".format(self.source, dest))

    def update_branch(self, dest):
        cmd = ("bzr", "pull", "-d", dest)
        return log_failure(cmd, "Updating {} from parent ({})".format(dest, self.source))

    def revno_branch(self, dest, revno):
        cmd = ('bzr', 'update', dest, '-r', revno)
        return log_failure(cmd, "Checking out revision {} of {}".format(revno, self.source))

    def normalize_lp_branch(self, branch):
        if branch.startswith('lp:'):
            if not '~' in branch:
                branch = branch.replace('lp:', 'lp:+branch/')
            branch = branch.replace('lp:', 'bzr+ssh://bazaar.launchpad.net/')
        return branch

    def is_same_branch(self, dest):
        self.source = strip_trailing_slash(self.source).strip()
        self.source = self.normalize_lp_branch(self.source)
        bzr_cmd = ("bzr", "info", dest)
        grep_cmd = ("grep", "parent branch")
        bzr_call = Popen(bzr_cmd, stdout=PIPE)
        grep_call = Popen(grep_cmd, stdin=bzr_call.stdout, stdout=PIPE)
        bzr_call.stdout.close()
        output = grep_call.communicate()[0].strip()
        if output:
            title, upstream = output.split(":", 1)
            self.dest_source = strip_trailing_slash(upstream).strip()
            return self.dest_source == self.source
        return False

    def is_bzr_branch(self, branch):
        branch = self.normalize_lp_branch(branch)
        bzr_cmd = ("bzr", "revno", branch)
        devnull = open('/dev/null', 'w')
        try:
           check_call(bzr_cmd, stdout=devnull)
           return True
        except CalledProcessError as e:
            if e.returncode == 3:
                return False
            else:
                raise e

    def get(self, dest, options=None):
        if not options:
            options = {}
        if not self.is_bzr_branch(self.source):
            raise NotABranch("{} is not a bzr branch. Is it a private branch? Check permissions on the branch.".format(self.source))
        if os.path.exists(dest):
            if not self.is_bzr_branch(dest):
                raise NotABranch("{} is not a bzr branch, it may be an empty directory".format(dest))
                return False
            # if the parent is the same, update the branch
            if self.is_same_branch(dest):
                if not self.update_branch(dest):
                    return False
            elif options.get("overwrite"):
                logging.info("Overwriting {}".format(dest))
                shutil.rmtree(dest)
                if not self.checkout_branch(dest):
                    return False
            else:
                raise NotSameBranch("{} failed: {} and {} do not match".format(dest, self.dest_source, self.source))
        else:
            if not self.checkout_branch(dest):
                return False
        if "revno" in options:
            self.revno_branch(dest, options["revno"])

        return True


class HttpFileHandler(SourceHandler):
    """Download plain files via http(s)"""

    schemes = (
        "http",
        "https",
    )

    def get(self, dest, options=None):
        if not options:
            options = {}
        if os.path.exists(dest):
            if options.get("overwrite"):
                os.unlink(dest)
            else:
                logging.info("Skipping existing dest {}".format(dest))
                return False
        logging.info("Downloading {} to {}".format(self.source, dest))
        try:
            response = urllib2.urlopen(self.source)
        except urllib2.URLError as e:
            logging.error("Failed to download {}: {}".format(self.source, e.reason))
            return False
        with open(dest, "w") as f:
            f.write(response.read())
        return True


class LocalHandler(SourceHandler):
    """Copy local files. The special source '@' indicates that the destination
    is a directory."""

    schemes = (
        '',
        'file',
    )

    def get(self, dest, options=None):
        if not options:
            options = {}

        if self.source == "@":
            logging.info("Creating directory {}".format(dest))
            fileutils.mkdir(dest, overwrite=options.get("overwrite", False))
            return True

        method = options.get("method", "copy")
        if method == "copy":
            logging.info("Copying {} to {}".format(self.source, dest))
            fileutils.copy(self.source, dest)
        elif method == "rsync":
            logging.info("Rsyncing {} to {}".format(self.source, dest))
            fileutils.rsync(self.source, dest)
        elif method == "link":
            logging.info("Creating symbolic link {} to {}".format(dest, self.source))
            fileutils.link(self.source, dest, overwrite=options.get(
                "overwrite", False))
        elif method == "hardlink":
            logging.info("Creating hard link {} to {}".format(dest, self.source))
            fileutils.link(self.source, dest, symbolic=False)

        return True


class DuplicateHandlerError(Exception):
    pass


def handler_types(handler_class=None):
    "Build a registry of handlers"
    if handler_class is None:
        handler_class = SourceHandler
    types = {}
    for subclass in handler_class.__subclasses__():
        for scheme in subclass.schemes:
            if scheme in types:
                new_handler = subclass.__name__
                old_handler = types[scheme].__name__
                raise DuplicateHandlerError("{} and {}".format(old_handler, new_handler))
            else:
                types[scheme] = subclass
    return types


class NoSuchHandlerError(Exception):
    pass


def handler_for_url(url):
    "Build a handler based on the given URL"
    if getattr(handler_types, "cache", None) is None:
        handler_types.cache = handler_types()
    scheme = urlparse(url).scheme
    if scheme in handler_types.cache:
        return handler_types.cache[scheme](url)
    raise NoSuchHandlerError("No handler found for URL: {}".format(url))

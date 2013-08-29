from urlparse import urlparse
import shutil
import subprocess
import os
import logging
import urllib2


class SourceHandler(object):
    handlers = {}

    def __init__(self, source):
        self.source = source

    @classmethod
    def handler_for(cls, url):
        return (h for h in cls.handlers if h.can_handle(url))


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

    def get(self, dest, options=None, overwrite=False):
        if not options:
            options = {}
        if overwrite and os.path.exists(dest):
            shutil.rmtree(dest)
        elif os.path.exists(dest):
            logging.info("Skipping existing dest {}".format(dest))
            return
        parent_dir = os.path.dirname(dest)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        cmd = ('bzr', 'branch', self.source, dest)
        logging.info("Branching {} to {}".format(self.source, dest))
        try:
            with open(os.devnull) as devnull:
                subprocess.check_output(cmd, stderr=devnull)
        except subprocess.CalledProcessError, e:
            logging.error(e.output)
        if "revno" in options:
            cmd = ('bzr', 'update', 'dest', '-r', options['revno'])


class HttpFileHandler(SourceHandler):
    """Download plain files via http(s)"""

    schemes = (
        "http",
        "https",
    )

    def get(self, dest, options=None, overwrite=False):
        if not options:
            options = {}
        if os.path.exists(dest):
            if overwrite:
                os.unlink(dest)
            else:
                logging.info("Skipping existing dest ()".format(dest))
                return
        logging.info("Downloading {} to {}".format(self.source, dest))
        try:
            response = urllib2.urlopen(self.source)
        except urllib2.URLError as e:
            logging.error("Failed to download {}: {}".format(self.source, e.reason))
        with open(dest, "w") as f:
            f.write(response.read())


class LocalHandler(SourceHandler):
    """Copy local files. The special source '@' indicates that the destination
    is a directory."""

    schemes = ('',)

    def get(self, dest, options=None, overwrite=False):
        if os.path.exists(dest):
            if overwrite:
                if os.path.isdir(dest):
                    shutil.rmtree(dest)
                else:
                    os.unlink(dest)
            else:
                logging.info("Skipping existing dest {}".format(dest))
        path = urlparse(self.source).path
        if path == "@":
            logging.info("Creating directory {}".format(dest))
            os.makedirs(dest)
        else:
            if os.path.isdir(self.source):
                logging.info("Copying directory {} to {}".format(self.source, dest))
                shutil.copytree(self.source, dest, symlinks=True)
            elif os.path.isfile(self.source):
                logging.info("Copying file {} to {}".format(self.source, dest))
                shutil.copy(self.source, self.dest)


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

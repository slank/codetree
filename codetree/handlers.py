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
        cmd = ('bzr', 'branch', self.source, dest)
        subprocess.check_call(cmd)
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
        response = urllib2.urlopen(self.source)
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
            os.makedirs(dest)
        else:
            if os.path.isdir(self.source):
                shutil.copytree(self.source, dest, symlinks=True)
            elif os.path.isfile(self.source):
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

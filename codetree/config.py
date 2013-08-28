from urlparse import urlparse
import fileinput
import heapq
from handlers import handler_for_url
import os


class InvalidDirective(Exception):
    pass


class Directive(object):
    @classmethod
    def from_raw_line(cls, raw_line, inpfile="??", lineno="??"):
        D = cls()
        D.location, source = raw_line.strip().split(None, 1)
        if urlparse(D.location).netloc:
            msg = "A local destination must be supplied: "
            msg += "{} (line {})".format(D.location, inpfile, lineno)
            raise InvalidDirective(msg)
        if os.path.isabs(D.location):
            msg = "Destinations must be relative paths: "
            msg += "{} (line {})".format(D.location, inpfile, lineno)
            raise InvalidDirective(msg)
        url, D.source_options = cls.parse_source(source)
        D.source = handler_for_url(url)
        return D

    @staticmethod
    def parse_source(source):
        options = {}
        if ";" in source:
            url, opt_string = source.strip().rsplit(";", 1)
            for opt in opt_string.split(","):
                options.update(dict((opt.split("="),)))
        else:
            url = source
        return url, options

    def run(self):
        self.source.get(self.location, self.source_options)


class Config(object):
    def __init__(self, config_files):
        self.directives = []
        raw_lines = fileinput.input(config_files)
        for raw_line in raw_lines:
            if self.ignored_line(raw_line):
                continue
            directive = Directive.from_raw_line(raw_line,
                                                inpfile=fileinput.filename(),
                                                lineno=fileinput.filelineno())
            heapq.heappush(self.directives, (len(directive.location), directive))

    def ignored_line(self, raw_line):
        "Blank lines and #Comments are ignored"
        line = raw_line.strip()
        if len(line) == 0:
            return True
        if line.startswith("#"):
            return True
        return False

    def build(self):
        for i in range(len(self.directives)):
            directive = heapq.heappop(self.directives)[1]
            directive.run()

from argparse import ArgumentParser
import logging
from .config import Config


def main():
    ap = ArgumentParser()
    ap.add_argument("cfgfile", nargs="+", help="Codetree configuration file")
    verbosity = ap.add_mutually_exclusive_group(required=False)
    verbosity.add_argument("-v", "--verbose", action="store_true", default=False)
    verbosity.add_argument("-q", "--quiet", action="store_true", default=False)

    args = ap.parse_args()

    logfmt = "%(message)s"
    loglevel = logging.INFO
    if args.verbose:
        logfmt = "%(levelname)s: %(message)s"
        loglevel = logging.DEBUG
    if args.quiet:
        loglevel = logging.CRITICAL
    logging.basicConfig(format=logfmt, level=loglevel)

    config = Config(args.cfgfile)
    config.build()

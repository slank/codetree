from argparse import ArgumentParser
import logging
from .config import Config


def main():
    logfmt = "%(msg)s"
    logging.basicConfig(level=logging.INFO, format=logfmt)

    ap = ArgumentParser()
    ap.add_argument("cfgfile", nargs="+", help="Codetree configuration file")

    args = ap.parse_args()
    config = Config(args.cfgfile)
    config.build()

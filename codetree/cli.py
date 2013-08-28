from argparse import ArgumentParser
from .config import Config


def main():
    ap = ArgumentParser()
    ap.add_argument("cfgfile", nargs="+", help="Codetree configuration file")

    args = ap.parse_args()
    config = Config(args.cfgfile)
    config.build()

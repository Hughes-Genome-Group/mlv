# Copyright 2017 Zegami Ltd

__doc__ = """Command line script to make a Zegami collection from KANJIDIC."""

import argparse
import sys

from . import (
    api,
    run,
)


def parse_args(argv):
    parser = argparse.ArgumentParser(argv[0], description=__doc__)
    parser.add_argument("--api-url", help="Zegami api endpoint")
    parser.add_argument("--project", help="Project id to make collection in")
    parser.add_argument("--token", help="Temp hack to use token over login")
    parser.add_argument("--dir", default="data", help="dir for output")
    parser.add_argument("--font", help="path of font")
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="show progress")
    parser.add_argument(
        "--also-212", action="store_true",
        help="include supplementary kanji from JIS X 0212-1990")
    parser.add_argument(
        "--use-zeg", action="store_true",
        help="create collection with zeg xslt template rather than images")
    args = parser.parse_args(argv[1:])
    if args.font is None:
        default_font = run.get_default_font()
        if default_font is None and not args.use_zeg:
            parser.error("no default fonts found, use --font")
        args.font = default_font
    return args


def main(argv):
    args = parse_args(argv)
    reporter = run.Reporter(sys.stderr, args.verbose)
    if args.api_url is None:
        client = None
    else:
        client = api.Client(args.api_url, args.project, args.token)
    try:
        run.create_collection(
            reporter, client, args.dir, args.font, args.also_212, args.use_zeg)
    except (EnvironmentError, ValueError) as e:
        sys.stderr.write("error: {}\n".format(e))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

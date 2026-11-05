"""Command line entry point for bmpkit.

The CLI is how most people meet a protocol library, so it is part of the public surface and
gets the same typing and testing discipline as the rest of the package.
"""

from __future__ import annotations

import argparse
import sys

USAGE = """\
Examples:
  bmpkit listen --listen 0.0.0.0:11019 --mirror ./captures"""


def build_parser():
    return argparse.ArgumentParser(
        prog="bmpkit",
        description="BGP Monitoring Protocol version 3 collector and decoder: initiation and peer distinguishing, route monitoring with path attributes, Adj-RIB-Out and Loc-RIB mirroring, statistics and route mirroring",
        epilog=USAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )


def main(argv=None):
    """Parse arguments, then refuse to pretend the protocol works.

    Exiting non-zero is the correct behaviour for a shell. A CLI that printed a friendly
    banner and exited 0 would be indistinguishable from one that actually did something.
    """
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_usage(sys.stderr)
    print("bmpkit: no protocol behaviour is implemented yet; see ROADMAP.md", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

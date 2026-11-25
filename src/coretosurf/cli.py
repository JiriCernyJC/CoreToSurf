"""Command line interface: ``coretosurf install-plugin`` and friends."""

import argparse
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="coretosurf",
        description="CoreToSurf PyMOL plugin helper.")
    parser.add_argument("--version", action="store_true",
                        help="print the version and exit")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("install-plugin",
                       help="register the plugin in PyMOL's Plugin menu")
    p.add_argument("--plugdir", default=None,
                   help="plugin directory to use (default: first writable "
                        "user plugin directory, or PyMOL's default one)")
    sub.add_parser("uninstall-plugin",
                   help="remove the plugin from PyMOL's Plugin menu")

    args = parser.parse_args(argv)

    if args.version:
        from . import __version__
        print(__version__)
        return 0

    if args.command is None:
        parser.print_help()
        return 1

    try:
        import pymol.plugins  # noqa: F401
    except ImportError as e:
        print("Error: cannot import PyMOL (%s).\nRun this with the Python "
              "environment that PyMOL uses." % e, file=sys.stderr)
        return 1

    from . import registration
    try:
        if args.command == "install-plugin":
            registration.install_plugin(args.plugdir, load_prefs=True)
        else:
            registration.uninstall_plugin(load_prefs=True)
    except Exception as e:
        print("Error: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

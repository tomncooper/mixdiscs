""" Main entry point for the Mixdiscer application """

import logging
import sys

from argparse import ArgumentParser, Namespace
from pathlib import Path

from mixdiscer.main import run, validate_playlists_from_files, render_all_playlists
from mixdiscer.validation import format_validation_results


def run_app(args: Namespace):
    """ Helper function to run the main Mixdiscer application """

    run(args.config)


def validate_app(args: Namespace):
    """ Helper function to validate playlist files """

    playlist_files = [Path(f) for f in args.files]

    results = validate_playlists_from_files(args.config, playlist_files)

    # Print results
    print(format_validation_results(results))

    # Exit with appropriate code
    all_valid = all(r.is_valid for r in results)
    sys.exit(0 if all_valid else 1)


def render_app(args: Namespace):
    """ Helper function to render all playlists to HTML """

    try:
        render_all_playlists(args.config, skip_errors=args.skip_errors)
        sys.exit(0)
    except Exception as e:
        logging.error("Rendering failed: %s", e)
        sys.exit(1)


def create_parser():
    """ Creates the argument parser for the Mixdiscer application """

    parser = ArgumentParser(description="Mixdiscer: The processor of mixdiscs")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command (default behavior)
    run_parser = subparsers.add_parser("run", help="Process all playlists in directory")
    run_parser.add_argument("config", help="Path to the configuration file")
    run_parser.set_defaults(func=run_app)

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate specific playlist files")
    validate_parser.add_argument("config", help="Path to the configuration file")
    validate_parser.add_argument("--files", nargs="+", required=True, help="Playlist files to validate")
    validate_parser.set_defaults(func=validate_app)

    # Render command
    render_parser = subparsers.add_parser("render", help="Render all playlists to HTML")
    render_parser.add_argument("config", help="Path to the configuration file")
    render_parser.add_argument(
        "--skip-errors",
        action="store_true",
        help="Continue rendering even if some playlists fail"
    )
    render_parser.set_defaults(func=render_app)

    return parser


if __name__ == "__main__":

    ARGS = create_parser().parse_args()

    # Configure logging to log to the console
    if ARGS.debug:
        LEVEL = logging.DEBUG
    else:
        LEVEL = logging.INFO

    logging.basicConfig(
        level=LEVEL,
        format='%(asctime)s : %(name)s : %(levelname)s : %(message)s'
    )

    # If no command specified, show help
    if not hasattr(ARGS, 'func'):
        create_parser().print_help()
        sys.exit(1)

    ARGS.func(ARGS)

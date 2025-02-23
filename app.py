""" Main entry point for the Mixdiscer application """

import logging

from argparse import ArgumentParser, Namespace

from mixdiscer.main import run


def run_app(args: Namespace):
    """ Helper function to run the main Mixdiscer application """

    run(args.config)


def create_parser():
    """ Creates the argument parser for the Mixdiscer application """

    parser = ArgumentParser(description="Mixdiscer: The processor of mixdiscs")

    parser.set_defaults(func=run_app)

    parser.add_argument("config", help="Path to the configuration file")

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

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

    ARGS.func(ARGS)

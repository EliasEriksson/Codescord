from typing import *
import argparse


class ParseError(Exception):
    pass


class ArgumentParser(argparse.ArgumentParser):
    """
    subclass of ArgumentParser is required for the argument parser to not sys exit
    on an error.
    """
    def error(self, message):
        """
        stores the crashed parsers formatted help text and the error message in ParseError.

        :param message:
        :return:
        """
        raise ParseError(self.format_help(), f": error: {message}")


def bool_validator(value):
    """
    changes a string on/off to true/false

    if not on/off is given raise error

    :param value: given value from command line
    :return:
    """
    if value not in ("on", "off"):
        raise argparse.ArgumentTypeError(f"state must be 'on' or 'off' not '{value}'")
    return True if value == "on" else False


"""
parser setup
"""
parser = ArgumentParser(prog="")
codescord_sub_parser = parser.add_subparsers()
codescord_parser = codescord_sub_parser.add_parser("/codescord")

options_sub_parser = codescord_parser.add_subparsers(
    dest="option", required=True
)

auto_run = options_sub_parser.add_parser(
    "auto-run",
    help=": option for codescord."
)
auto_run.add_argument(
    "value", type=bool_validator,
    help="on/off if you want to auto run highlighted code blocks."
)


def parse(message: str) -> Tuple[Union[argparse.Namespace, Tuple[str, ...]], bool]:
    """
    parses a string for command line use

    use the tuples second value to determine if the parse was successful or not

    if the returned tuples second value is false the first will be a string
    if the returned tuples second value is true the first will be a argparse.Namespace

    :param message: command line string
    :return: tuple with message and boolean if it errored
    """
    try:
        results = parser.parse_args(message.lower().split())
        for key in dir(results):
            if not key.startswith("_"):
                try:
                    if "-" in getattr(results, key):
                        setattr(results, key, getattr(results, key).replace("-", "_"))
                except TypeError:
                    pass
        return results, False
    except ParseError as error:
        return error.args, True


if __name__ == '__main__':
    pass
    try:
        r = parser.parse_args()
        for option in dir(r):
            if not option.startswith("_"):
                try:
                    if "-" in getattr(r, option):
                        setattr(r, option, getattr(r, option).replace("-", "_"))
                except TypeError:
                    pass
        print(r)
    except ParseError as e:
        print("\n".join(e.args))

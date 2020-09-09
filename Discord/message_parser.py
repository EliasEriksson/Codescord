from typing import *
import argparse


class ParseError(Exception):
    pass


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ParseError(self.format_help(), f": error: {message}")


def state_validator(value):
    if value not in ("on", "off"):
        raise argparse.ArgumentTypeError(f"state must be 'on' or 'off' not '{value}'")
    return True if value == "on" else False


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
    "value", type=state_validator,
    help="on/off if you want to auto run highlighted code blocks."
)


def parse(message: str) -> Tuple[Union[argparse.Namespace, Tuple[str, ...]], bool]:
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

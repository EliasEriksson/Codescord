from typing import *


def autocast_to_annotations(func):
    def wrapper(*args, **kwargs):
        args = (type(arg)(value) if not isinstance(value, func.__annotations__[arg]) else value
                for arg, value in zip(func.__code__.co_varnames, args))
        return func(*args)
    return wrapper

@autocast_to_annotations
def foo(x: bool, a: str, b: str, ) -> str:
    print(x)
    return a + b


result = foo(True, 1, 2, asd="123")
print(result)

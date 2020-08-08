from typing import *


def autocast_to_annotations(func):
    def wrapper(*args, **kwargs):
        # inspecting args
        args = list(args)
        m = dict(list(zip(
                func.__code__.co_varnames, range(len(func.__code__.co_varnames)))
            )[:func.__code__.co_argcount]
        )
        for arg, index in m.items():
            if arg in func.__annotations__:
                t = func.__annotations__[arg]
                value = args[index]
                correct_type = isinstance(value, t)
                if not correct_type:
                    args[index] = t(value)
        # inspecting kwargs
        for kwarg, value in kwargs.items():
            if kwarg in func.__annotations__:
                t = func.__annotations__[kwarg]
                correct_type = isinstance(value, t)
                if not correct_type:
                    kwargs[kwarg] = t(value)

        return func(*args, **kwargs)
    return wrapper


@autocast_to_annotations
def foo(x: bool, a: str, b: str, ) -> str:
    print(x)
    return a + b


result = foo(True, 1, 2, asd="123")
print(result)

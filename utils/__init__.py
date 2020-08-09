def cast_to_annotations(func):
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


class Protocol:
    buffer_size = 1
    max_buffer = 128
    timeout = 30

    success = 0
    awaiting = 1
    internal_server_error = 2
    not_implemented = 3
    close = 4

    file = 10
    authenticate = 11
    text = 12

    @classmethod
    def get_protocol(cls) -> str:
        attrs = []
        for attr in dir(cls):
            if attr.startswith("__"):
                continue
            if callable((value := getattr(cls, attr))):
                if "__func__" not in dir(value):
                    for inner_attr in dir(value):
                        if not inner_attr.startswith("__"):
                            attrs.append(f"{inner_attr}={getattr(getattr(cls, attr), inner_attr)}")
            else:
                attrs.append(f"{attr}={value}")
        attrs.sort()
        return ":".join(attrs)


__all__ = ["Protocol", "cast_to_annotations", "Protocol"]


if __name__ == '__main__':
    print(Protocol.get_protocol())

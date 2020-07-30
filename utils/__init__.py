def cast_to_annotations(func):
    def wrapper(*args):
        print(len(args))
        print(args)
        args = (type(arg)(value) if not isinstance(value, func.__annotations__[arg]) else value
                for arg, value in zip(func.__code__.co_varnames, args)
                )
        return func(*args)
    return wrapper


class Protocol:
    buffer_size = 128

    class Instructions:
        protocol = "protocol"
        file = "file"
        text = "text"

    class StatusCodes:
        success = b"200"
        failed = b"400"
        internal_server_error = b"500"
        not_implemented = b"501"
        close = b"600"

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


__all__ = ["Protocol", "cast_to_annotations"]


if __name__ == '__main__':
    print(P.get_protocol())

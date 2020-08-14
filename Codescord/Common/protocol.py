class Protocol:
    buffer_size = 1
    max_buffer = 128
    timeout = 30

    class Status:
        success = 0
        awaiting = 1
        close = 2

        internal_server_error = 10
        language_not_implemented = 11
        not_implemented = 12
        process_timeout = 13

        file = 20
        authenticate = 21
        text = 22

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

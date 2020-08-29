class Protocol:
    """
    this is the communication protocol that is expected to be the same on the client and the server.

    contains general values and Status codes for the server and client.
    """
    buffer_size = 1
    max_buffer = 128
    timeout = 30

    class Status:
        """
        status codes.
        success: sent back if anything was done successfully.
        awaiting: sent back if the client ore server expects more data.
        close: closes the connection.

        10 < status < 20: various errors.

        20 < status: execution instructions that are sent to tell server/client what to expect.
        file: a file will be sent, prepare to download.
        authenticate: authenticate the protocol and make sure we speak the same protocol.
        text: text will be sent prepare to download.
        """
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
        """
        generates a string that represents the protocol.

        the server can compare the clients and its own protocol to make sure they match.

        :return: protocol as text.
        """
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

class ProcessTimedOut(Exception):
    pass


class NotImplementedByServer(Exception):
    pass


class NotImplementedByClient(Exception):
    pass


class InternalServerError(Exception):
    pass


class MaximumRetries(Exception):
    pass

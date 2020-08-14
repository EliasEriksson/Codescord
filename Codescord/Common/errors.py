class Errors:
    class ProcessTimedOut(Exception):
        pass

    class NotImplementedByServer(NotImplementedError):
        pass

    class NotImplementedByClient(NotImplementedError):
        pass

    class InternalServerError(Exception):
        pass

    class MaximumRetries(Exception):
        pass

    class DownloadError(Exception):
        pass

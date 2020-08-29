class Errors:
    class ProcessTimedOut(Exception):
        pass

    class LanguageNotImplementedByServer(NotImplementedError):
        pass

    class NotImplementedByRecipient(NotImplementedError):
        pass

    class NotImplementedInProtocol(NotImplementedError):
        pass

    class InternalServerError(Exception):
        pass


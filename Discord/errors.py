class Errors:
    class ContainerStartupError(Exception):
        pass

    class ContainerStopError(Exception):
        pass

    class ContainerRmError(Exception):
        pass

class Source:
    def __init__(self, language: str, code: str, sys_args: str = None) -> None:
        self.language = language
        self.code = code
        self.sys_args = sys_args

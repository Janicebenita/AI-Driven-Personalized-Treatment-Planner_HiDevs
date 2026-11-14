"""Safe, actionable operational errors without provider bodies or patient data."""


class ProviderError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

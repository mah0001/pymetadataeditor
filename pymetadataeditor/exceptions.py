"""Package-specific exceptions."""


class DeleteNotAppliedError(Exception):
    """Exception raised when a delete request is not accepted by the system."""

    def __init__(self, message="Delete request not accepted by system.", response=None):
        super().__init__(message)
        self.response = response


class TemplateError(Exception):
    """Exception raised when there is an error with a template."""

    def __init__(self, message="Error with template", response=None):
        super().__init__(message)
        self.message = message
        self.response = response

    def __str__(self):
        if self.response:
            return f"{self.response}\n\n{self.message}"
        return self.message

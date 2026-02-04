class WorkflowError(Exception):
    """Base error for workflow loading and validation."""


class WorkflowLoadError(WorkflowError):
    """Raised when workflow files cannot be read or parsed."""


class WorkflowValidationError(WorkflowError):
    """Raised when workflow content fails schema validation."""

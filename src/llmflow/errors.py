class WorkflowError(Exception):
    """Base error for workflow loading and validation."""


class WorkflowLoadError(WorkflowError):
    """Raised when workflow files cannot be read or parsed."""


class WorkflowValidationError(WorkflowError):
    """Raised when workflow content fails schema validation."""


class GraphError(Exception):
    """Base error for graph construction and ordering."""


class GraphDependencyError(GraphError):
    """Raised when a step depends on an unknown step."""


class GraphCycleError(GraphError):
    """Raised when a cycle is detected in the workflow graph."""


class RegistryError(Exception):
    """Base error for registry operations."""


class StepRegistrationError(RegistryError):
    """Raised when a step type registration is invalid."""


class StepNotFoundError(RegistryError):
    """Raised when a step type is not registered."""


class ProviderError(Exception):
    """Base error for provider operations."""

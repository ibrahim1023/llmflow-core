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


class StepExecutionError(Exception):
    """Base error for step execution failures."""


class LLMConfigError(StepExecutionError):
    """Raised when LLM step configuration is missing or invalid."""


class LLMRenderError(StepExecutionError):
    """Raised when an LLM prompt template fails to render."""


class LLMOutputSchemaError(StepExecutionError):
    """Raised when an LLM output schema cannot be loaded or parsed."""


class LLMOutputValidationError(StepExecutionError):
    """Raised when an LLM output fails JSON schema validation."""

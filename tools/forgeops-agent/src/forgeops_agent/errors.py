class AgentError(RuntimeError):
    """Base error shown by the ForgeOps agent CLI."""


class ConfigurationError(AgentError):
    pass


class PolicyError(AgentError):
    pass


class TaskNotFoundError(AgentError):
    pass


class LockError(AgentError):
    pass


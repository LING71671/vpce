"""Error taxonomy shared by every layer.

Deliberately free of any Visual Paradigm knowledge: adapters translate their
own failures into these types so the service and transports can stay generic.
"""


class VpceError(RuntimeError):
    """Base class for everything this package raises."""


class ConfigurationError(VpceError):
    """Installation or plugin layout is wrong; the user has to fix something."""


class EditionGate(VpceError):
    """The command exists but the installed edition does not allow it."""


class ProjectLocked(VpceError):
    """Another process (usually the GUI) holds the project."""


class UpgradeRequired(VpceError):
    """Project file predates the installed build."""


class CommandFailure(VpceError):
    def __init__(self, command, returncode, output):
        self.command = command
        self.returncode = returncode
        self.output = output or ''
        super().__init__('%s failed (rc=%d): %s'
                         % (command, returncode, _tail(self.output)))


class SpecError(VpceError):
    """The drawing spec is malformed."""


def _tail(text, limit=1200):
    text = (text or '').strip()
    return text[-limit:] if len(text) > limit else text

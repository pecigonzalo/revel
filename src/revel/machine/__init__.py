import pkg_resources

__version__ = pkg_resources.get_distribution(__name__).version

from .machine import Machine
from .manager import MachineManager
from .state import State

__all__ = (
    "Machine",
    "MachineManager",
    "State",
)

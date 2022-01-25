import pkg_resources

__version__ = pkg_resources.get_distribution(__name__).version

from .config import Config
from .machine import MachineManager

__all__ = (
    "Config",
    "MachineManager",
)

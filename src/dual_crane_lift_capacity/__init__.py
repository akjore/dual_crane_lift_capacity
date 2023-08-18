"""pint needs to be centralized."""
from importlib.metadata import PackageNotFoundError, version

from pint import UnitRegistry

ureg = UnitRegistry()
Q = ureg.Quantity

try:
    __version__ = version("dual_crane_lift_capacity")
except PackageNotFoundError:
    __version__ = "unknown version"

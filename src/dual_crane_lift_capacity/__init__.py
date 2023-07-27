from importlib.metadata import version, PackageNotFoundError

from pint import UnitRegistry


ureg = UnitRegistry()
Q = ureg.Quantity

try:
    __version__ = version("dual_crane_lift_capacity")
except PackageNotFoundError:
    __version__ = "unknown version"

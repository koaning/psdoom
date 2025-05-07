"""
PSDoom - A terminal-based process manager inspired by the classic Doom game.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("psdoom")
except PackageNotFoundError:
    # Package is not installed, use default version
    __version__ = "0.1.0"

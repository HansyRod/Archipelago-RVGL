from dataclasses import dataclass

from Options import PerGameCommonOptions


@dataclass
class RVGLOptions(PerGameCommonOptions):
    """RVGL options, initially using only Archipelago's common settings."""

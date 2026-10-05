"""
Minimal, deterministic configuration for Finance-Model-Testbench.
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass(frozen=True)
class TestbenchConfig:
    """
    Immutable configuration settings for testbench execution environment.
    """
    __test__ = False
    environment: str = "development"
    allow_network: bool = False
    strict_tolerance: bool = True
    extra_options: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as a dictionary."""
        return {
            "environment": self.environment,
            "allow_network": self.allow_network,
            "strict_tolerance": self.strict_tolerance,
            "extra_options": dict(self.extra_options),
        }

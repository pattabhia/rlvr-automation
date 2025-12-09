"""
Adapters Package - Concrete Implementations

Adapters connect the core domain to external systems.
They are split into:
- input/: Primary/Driving adapters (UI, CLI, API)
- output/: Secondary/Driven adapters (DB, external APIs)
"""

# Re-export for convenience
from .input import *
from .output import *

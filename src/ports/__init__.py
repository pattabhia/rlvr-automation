"""
Ports Package - Interfaces for Hexagonal Architecture

Ports define contracts between core domain and external systems.
They are split into:
- input/: Primary/Driving ports (what the app offers)
- output/: Secondary/Driven ports (what the app needs)
"""

# Re-export all ports for convenience
from .input import *
from .output import *

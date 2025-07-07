"""Department coordination infrastructure for HeyJarvis.

This module provides the base architecture for department-level coordination,
allowing multiple micro-agents to work together on complex business objectives.
"""

from .base_department import Department, DepartmentOrchestrator

__all__ = ["Department", "DepartmentOrchestrator"]
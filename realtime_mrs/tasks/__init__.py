"""
Task implementations for the realtime-mrs package.

This module provides experimental task implementations that can be used
with the PsychoPy display manager or standalone.

Available tasks:
- BaseTask: Abstract base class for all tasks
- M1TappingTask: Motor cortex finger tapping task
- V1OrientationTask: Visual cortex orientation discrimination task
- EIVisualizationTask: E/I ratio visualization task
"""

from .base import BaseTask, TaskConfig, TaskResult
from .m1_tapping import M1TappingTask
from .v1_orientation import V1OrientationTask
from .ei_visualization import EIVisualizationTask

__all__ = [
    'BaseTask',
    'TaskConfig',
    'TaskResult',
    'M1TappingTask',
    'V1OrientationTask',
    'EIVisualizationTask',
] 
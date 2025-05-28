"""
Realtime MRS - Real-time MRS visualization system with FSL-MRS and Lab Streaming Layer integration.

This package provides modular components for:
- Real-time MRS data processing and visualization
- Lab Streaming Layer (LSL) integration
- PsychoPy-based experimental tasks
- Data recording and analysis
- Network communication (TCP/LSL)

Main modules:
- core: Core utilities (logging, configuration, etc.)
- tasks: Experimental task implementations
- display: PsychoPy display management
- data: Data processing and analysis
- lsl: Lab Streaming Layer integration
- network: Network communication components
- testing: Testing utilities

Example usage:
    >>> from realtime_mrs.core import get_logger, load_config
    >>> from realtime_mrs.tasks import M1TappingTask, V1OrientationTask
    >>> from realtime_mrs.display import PsychoPyDisplayManager
    >>> from realtime_mrs.lsl import FSLMRSLSLPublisher
"""

__version__ = "0.2.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Import main components for easy access
from .core.logger import get_logger, setup_logging
from .core.config import load_config, get_config
from .core.utils import ensure_data_dir, validate_config

# Import main classes
try:
    from .display.psychopy_manager import PsychoPyDisplayManager
except ImportError:
    # PsychoPy might not be available
    PsychoPyDisplayManager = None

try:
    from .lsl.fsl_mrs_publisher import FSLMRSLSLPublisher
    from .lsl.receiver import LSLReceiver
except ImportError:
    # LSL might not be available
    FSLMRSLSLPublisher = None
    LSLReceiver = None

from .tasks.base import BaseTask
from .tasks.m1_tapping import M1TappingTask
from .tasks.v1_orientation import V1OrientationTask

# Define what gets imported with "from realtime_mrs import *"
__all__ = [
    # Version info
    '__version__',
    '__author__',
    '__email__',
    
    # Core utilities
    'get_logger',
    'setup_logging',
    'load_config',
    'get_config',
    'ensure_data_dir',
    'validate_config',
    
    # Main classes
    'PsychoPyDisplayManager',
    'FSLMRSLSLPublisher',
    'LSLReceiver',
    'BaseTask',
    'M1TappingTask',
    'V1OrientationTask',
]

# Package metadata
__title__ = "realtime-mrs"
__description__ = "Real-time MRS visualization system with FSL-MRS and Lab Streaming Layer integration"
__url__ = "https://github.com/yourusername/realtime-mrs"
__license__ = "MIT"
__copyright__ = "Copyright 2024" 
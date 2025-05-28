# Migration Guide: From Legacy to Modular Structure

This guide helps you migrate from the legacy realtime-mrs code structure to the new modular package.

## Overview of Changes

The codebase has been restructured from a collection of standalone scripts to a proper Python package with modular components. This provides better reusability, maintainability, and easier integration into other projects.

## Key Changes

### 1. Package Structure

**Before (Legacy):**
```
realtime-mrs/
├── menu.py
├── logger.py
├── config.py
├── config.yaml
├── m1_tapping_task.py
├── v1_orientation_task.py
├── psychopy_display_manager.py
├── fsl_mrs_lsl_publisher.py
├── lsl_ei_receiver.py
├── ei_tcp_event_listener.py
├── sent_ei.py
├── data_analysis.py
├── experiment_data_recorder.py
└── ... (other standalone files)
```

**After (Modular):**
```
realtime_mrs/
├── __init__.py              # Main package interface
├── cli.py                   # Command-line interface
├── core/                    # Core utilities
│   ├── logger.py
│   ├── config.py
│   └── utils.py
├── tasks/                   # Task implementations
│   ├── base.py
│   ├── m1_tapping.py
│   ├── v1_orientation.py
│   └── ei_visualization.py
├── display/                 # Display management
│   └── psychopy_manager.py
├── lsl/                     # LSL integration
│   ├── fsl_mrs_publisher.py
│   ├── receiver.py
│   └── data_generator.py
├── data/                    # Data processing
│   ├── recorder.py
│   ├── analysis.py
│   └── visualization.py
├── network/                 # Network communication
│   ├── tcp_server.py
│   └── tcp_client.py
└── testing/                 # Testing utilities
    └── test_lsl_system.py
```

### 2. Import Changes

**Before:**
```python
from logger import get_logger
from config import get_config
import m1_tapping_task
import psychopy_display_manager
```

**After:**
```python
from realtime_mrs.core import get_logger, get_config
from realtime_mrs.tasks import M1TappingTask
from realtime_mrs.display import PsychoPyDisplayManager
```

### 3. Configuration Management

**Before:**
```python
# config.py
import yaml
CONFIG_PATH = 'config.yaml'

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

def get_config(path, default=None):
    # Simple dot notation access
    pass
```

**After:**
```python
# Enhanced configuration with multiple sources
from realtime_mrs.core import load_config, get_config

# Supports multiple config sources:
# 1. Default config (built-in)
# 2. Package config file
# 3. Project config file  
# 4. User config file (~/.realtime_mrs/config.yaml)
# 5. Environment variables (REALTIME_MRS_*)
# 6. Explicit config file

config = load_config("my_config.yaml")  # Optional explicit file
value = get_config("network.port", 8080)  # Dot notation with default
```

### 4. Task Implementation

**Before:**
```python
# m1_tapping_task.py
def run_m1_experiment(win, m1_config, logger):
    # Task implementation directly in function
    pass
```

**After:**
```python
# realtime_mrs/tasks/m1_tapping.py
from .base import BaseTask, TaskConfig

class M1TappingTask(BaseTask):
    def setup(self, **kwargs):
        # Setup logic
        return True
    
    def run_trial(self, trial_number, **kwargs):
        # Trial logic
        return trial_data
    
    def cleanup(self):
        # Cleanup logic
        return True

# Usage:
config = TaskConfig(
    task_name="m1_tapping",
    participant_id="P001",
    task_params={'n_trials': 10}
)
task = M1TappingTask(config)
result = task.run()
```

### 5. Logging

**Before:**
```python
# logger.py
import logging
_logging_configured = False

def setup_logging():
    # Basic logging setup
    pass

def get_logger(name):
    # Simple logger creation
    pass
```

**After:**
```python
# Enhanced logging with better configuration
from realtime_mrs.core import setup_logging, get_logger

# More flexible setup
setup_logging(
    log_file="my_experiment.log",
    log_level="DEBUG",
    console_level="INFO"
)

logger = get_logger("my_module")  # Automatic package prefixing
```

## Migration Steps

### Step 1: Install the New Package

```bash
# If you have the new modular code
pip install -e .

# Or install from PyPI (when available)
pip install realtime-mrs
```

### Step 2: Update Imports

Replace your old imports with the new modular imports:

```python
# OLD
from logger import get_logger
 
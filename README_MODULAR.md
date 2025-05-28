# Realtime MRS - Modular Package

A modular Python package for real-time MRS (Magnetic Resonance Spectroscopy) visualization with FSL-MRS and Lab Streaming Layer (LSL) integration.

## Overview

This package has been restructured into a modular design that allows you to easily reuse components in different projects. The package provides:

- **Core utilities**: Logging, configuration, and common utilities
- **Task implementations**: Experimental tasks (M1 tapping, V1 orientation, E/I visualization)
- **Display management**: PsychoPy-based display management
- **LSL integration**: Lab Streaming Layer publishers and receivers
- **Data processing**: Data recording, analysis, and visualization
- **Network communication**: TCP and LSL communication components

## Installation

### From Source (Development)

```bash
# Clone the repository
git clone <repository-url>
cd realtime-mrs

# Install in development mode
pip install -e .

# Or with optional dependencies
pip install -e ".[psychopy,dev]"
```

### As a Package

```bash
# Install from PyPI (when published)
pip install realtime-mrs

# With optional dependencies
pip install "realtime-mrs[psychopy]"
```

## Quick Start

### Command Line Interface

The package provides a comprehensive CLI:

```bash
# Check dependencies
realtime-mrs check-deps

# Show system information
realtime-mrs info

# Launch interactive menu
realtime-mrs menu

# Start LSL publisher
realtime-mrs lsl-publisher --simulation

# Start LSL receiver
realtime-mrs lsl-receiver

# Run specific tasks
realtime-mrs task m1 --participant P001 --trials 5
realtime-mrs task v1 --participant P001 --trials 20
realtime-mrs task ei --participant P001

# Configuration management
realtime-mrs config --show
realtime-mrs config --set network.port 8080
realtime-mrs config --save my_config.yaml

# Test LSL system
realtime-mrs test-lsl --duration 30
```

### Python API

#### Basic Usage

```python
from realtime_mrs import get_logger, load_config
from realtime_mrs.tasks import M1TappingTask, TaskConfig
from realtime_mrs.lsl import FSLMRSLSLPublisher

# Setup logging
logger = get_logger("my_experiment")

# Load configuration
config = load_config("my_config.yaml")

# Create and run a task
task_config = TaskConfig(
    task_name="m1_tapping",
    participant_id="P001",
    session_id="session_001",
    task_params={'n_trials': 10}
)

task = M1TappingTask(task_config)
result = task.run()

print(f"Task completed: {result.completed}")
print(f"Duration: {result.duration:.1f}s")
```

#### Using Individual Components

```python
# Core utilities
from realtime_mrs.core import get_logger, load_config, ensure_data_dir
from realtime_mrs.core.utils import Timer, ThreadSafeCounter

# Logging
logger = get_logger("my_module")
logger.info("Starting my experiment")

# Configuration
config = load_config()
sampling_rate = config.get('lsl.sampling_rate', 1.0)

# Data directory
data_dir = ensure_data_dir("my_experiment_data")

# Utilities
timer = Timer()
timer.start()
# ... do work ...
elapsed = timer.stop()
logger.info(f"Work completed in {elapsed:.2f}s")
```

#### LSL Integration

```python
from realtime_mrs.lsl import FSLMRSLSLPublisher, LSLReceiver

# Publisher
publisher = FSLMRSLSLPublisher()
publisher.start_streaming()

# Receiver
receiver = LSLReceiver(stream_name="FSL-MRS-EI-Ratio")
receiver.start()

# Get data
data = receiver.get_latest_data()
if data:
    print(f"Latest E/I ratio: {data['value']}")
```

#### Task Development

```python
from realtime_mrs.tasks import BaseTask, TaskConfig, TaskResult

class MyCustomTask(BaseTask):
    def setup(self, **kwargs):
        self.logger.info("Setting up my custom task")
        # Initialize your task here
        return True
    
    def run_trial(self, trial_number, **kwargs):
        # Implement your trial logic
        trial_data = {
            'trial_number': trial_number,
            'response_time': 1.23,
            'accuracy': True,
        }
        return trial_data
    
    def cleanup(self):
        self.logger.info("Cleaning up my custom task")
        return True
    
    def get_trial_count(self):
        return self.config.task_params.get('n_trials', 10)

# Use your custom task
config = TaskConfig(
    task_name="my_custom_task",
    participant_id="P001",
    task_params={'n_trials': 20}
)

task = MyCustomTask(config)
result = task.run()
```

## Package Structure

```
realtime_mrs/
├── __init__.py              # Main package interface
├── cli.py                   # Command-line interface
├── menu.py                  # Interactive menu (legacy compatibility)
├── core/                    # Core utilities
│   ├── __init__.py
│   ├── logger.py           # Logging configuration
│   ├── config.py           # Configuration management
│   └── utils.py            # Common utilities
├── tasks/                   # Task implementations
│   ├── __init__.py
│   ├── base.py             # Base task class
│   ├── m1_tapping.py       # M1 tapping task
│   ├── v1_orientation.py   # V1 orientation task
│   └── ei_visualization.py # E/I visualization task
├── display/                 # Display management
│   ├── __init__.py
│   └── psychopy_manager.py # PsychoPy display manager
├── lsl/                     # LSL integration
│   ├── __init__.py
│   ├── fsl_mrs_publisher.py # FSL-MRS LSL publisher
│   ├── receiver.py         # LSL receiver
│   └── data_generator.py   # Data generation utilities
├── data/                    # Data processing
│   ├── __init__.py
│   ├── recorder.py         # Data recording
│   ├── analysis.py         # Data analysis
│   └── visualization.py    # Data visualization
├── network/                 # Network communication
│   ├── __init__.py
│   ├── tcp_server.py       # TCP server
│   └── tcp_client.py       # TCP client
├── testing/                 # Testing utilities
│   ├── __init__.py
│   └── test_lsl_system.py  # LSL system tests
└── config/                  # Configuration files
    └── __init__.py
```

## Configuration

The package supports flexible configuration through multiple sources:

1. **Default configuration** (built into the package)
2. **Package config file** (`config.yaml` in package directory)
3. **Project config file** (`config.yaml` in current directory)
4. **User config file** (`~/.realtime_mrs/config.yaml`)
5. **Environment variables** (with `REALTIME_MRS_` prefix)
6. **Explicit config file** (passed to functions)

### Configuration Example

```yaml
# config.yaml
global:
  participant_id: "P001"
  session_id: "session_001"
  data_dir: "data"
  log_level: "INFO"

network:
  ip: "127.0.0.1"
  port: 12345
  timeout: 5.0

lsl:
  stream_name: "RealtimeMRS"
  stream_type: "EI_Ratio"
  sampling_rate: 1.0

m1_task:
  controller: "keyboard"
  repetitions: 3
  sequence: ["4", "1", "3", "2", "4"]
  sequence_display_time: 2
  response_cutoff_time: 5

v1_task:
  stimulus_duration: 0.1
  n_trials: 20
  response_cutoff_time: 3

fsl_mrs_lsl:
  simulation_mode: true
  simulation_range: [0.3, 1.2]
  simulation_noise: 0.05
```

### Environment Variables

```bash
# Override configuration with environment variables
export REALTIME_MRS_NETWORK_PORT=8080
export REALTIME_MRS_LSL_SAMPLING_RATE=2.0
export REALTIME_MRS_GLOBAL_LOG_LEVEL=DEBUG
```

## Using in Other Projects

### Example 1: Simple E/I Ratio Monitoring

```python
# my_monitoring_app.py
from realtime_mrs.lsl import LSLReceiver
from realtime_mrs.core import get_logger
import time

logger = get_logger("monitoring")

# Connect to E/I ratio stream
receiver = LSLReceiver(stream_name="FSL-MRS-EI-Ratio")
receiver.start()

logger.info("Monitoring E/I ratio...")

try:
    while True:
        data = receiver.get_latest_data()
        if data:
            ei_ratio = data['value']
            timestamp = data['timestamp']
            logger.info(f"E/I Ratio: {ei_ratio:.3f} at {timestamp}")
        
        time.sleep(1.0)
        
except KeyboardInterrupt:
    logger.info("Monitoring stopped")
    receiver.stop()
```

### Example 2: Custom Experimental Task

```python
# my_experiment.py
from realtime_mrs.tasks import BaseTask, TaskConfig
from realtime_mrs.display import PsychoPyDisplayManager
from realtime_mrs.core import get_logger

class AttentionTask(BaseTask):
    def setup(self, **kwargs):
        # Initialize PsychoPy display
        self.display = kwargs.get('display')
        if not self.display:
            self.display = PsychoPyDisplayManager()
            self.display.setup()
        
        self.logger.info("Attention task setup complete")
        return True
    
    def run_trial(self, trial_number, **kwargs):
        # Show stimulus
        self.display.show_text("Focus on the center", duration=2.0)
        
        # Collect response
        start_time = time.time()
        response = self.display.wait_for_key(['space'], timeout=3.0)
        reaction_time = time.time() - start_time
        
        return {
            'trial_number': trial_number,
            'reaction_time': reaction_time,
            'response': response,
        }
    
    def cleanup(self):
        if hasattr(self, 'display'):
            self.display.close()
        return True

# Run the experiment
if __name__ == "__main__":
    config = TaskConfig(
        task_name="attention_task",
        participant_id="P001",
        task_params={'n_trials': 50}
    )
    
    task = AttentionTask(config)
    result = task.run()
    
    print(f"Experiment completed: {result.completed}")
    print(f"Data saved to: {result.data_files}")
```

### Example 3: Real-time Data Processing Pipeline

```python
# my_pipeline.py
from realtime_mrs.lsl import LSLReceiver
from realtime_mrs.data import DataRecorder, DataAnalyzer
from realtime_mrs.core import get_logger, ensure_data_dir
import numpy as np

logger = get_logger("pipeline")

class RealTimeProcessor:
    def __init__(self):
        self.receiver = LSLReceiver(stream_name="FSL-MRS-EI-Ratio")
        self.recorder = DataRecorder(ensure_data_dir("processed_data"))
        self.analyzer = DataAnalyzer()
        self.buffer = []
        
    def start(self):
        self.receiver.start()
        logger.info("Real-time processing started")
        
        try:
            while True:
                # Get new data
                data = self.receiver.get_latest_data()
                if data:
                    self.process_sample(data)
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.stop()
    
    def process_sample(self, data):
        # Add to buffer
        self.buffer.append(data['value'])
        
        # Keep buffer size manageable
        if len(self.buffer) > 100:
            self.buffer.pop(0)
        
        # Analyze if we have enough data
        if len(self.buffer) >= 10:
            # Calculate moving average
            moving_avg = np.mean(self.buffer[-10:])
            
            # Detect significant changes
            if len(self.buffer) >= 20:
                recent_avg = np.mean(self.buffer[-10:])
                previous_avg = np.mean(self.buffer[-20:-10])
                change = abs(recent_avg - previous_avg)
                
                if change > 0.1:  # Threshold for significant change
                    logger.info(f"Significant E/I change detected: {change:.3f}")
                    
                    # Record event
                    self.recorder.record_event({
                        'timestamp': data['timestamp'],
                        'ei_ratio': data['value'],
                        'moving_average': moving_avg,
                        'change_magnitude': change,
                        'event_type': 'significant_change'
                    })
    
    def stop(self):
        self.receiver.stop()
        self.recorder.close()
        logger.info("Real-time processing stopped")

# Run the pipeline
if __name__ == "__main__":
    processor = RealTimeProcessor()
    processor.start()
```

## Dependencies

### Core Dependencies
- `numpy>=1.21.0`
- `scipy>=1.7.0`
- `matplotlib>=3.5.0`
- `pandas>=1.3.0`
- `pyyaml>=6.0`

### Optional Dependencies
- `pylsl>=1.16.0` (for LSL integration)
- `psychopy>=2023.1.0` (for display management)
- `pygame>=2.0.0` (for input handling)
- `seaborn>=0.13.2` (for enhanced plotting)

### Development Dependencies
- `pytest>=7.0`
- `black>=23.0`
- `flake8>=6.0`
- `mypy>=1.0`

## Testing

```bash
# Run dependency check
realtime-mrs check-deps

# Test LSL system
realtime-mrs test-lsl --duration 10

# Run unit tests (if pytest is installed)
pytest tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Check the documentation
- Run `realtime-mrs check-deps` to verify your setup
- Use `realtime-mrs info` to get system information
- Create an issue on the repository

## Changelog

### Version 0.2.0
- Restructured into modular package
- Added comprehensive CLI interface
- Improved configuration management
- Enhanced logging system
- Added base task class for easy extension
- Better error handling and validation
- Comprehensive documentation and examples 
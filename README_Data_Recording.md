# Realtime MRS Data Acquisition and Recording System

This document describes the comprehensive data acquisition and recording system for the Realtime MRS experiment platform, built on Lab Streaming Layer (LSL) for synchronized, multi-modal data collection.

## Overview

The system provides centralized data acquisition and recording across all experiment components:

- **FSL-MRS E/I Ratio Data**: Real-time excitatory/inhibitory ratio measurements
- **Task Performance Data**: M1 tapping and V1 orientation task responses
- **Physiological Data**: Heart rate, eye tracking, and other biosignals
- **Experiment Events**: Session markers, interventions, and timing events

## Architecture

### Core Components

1. **ExperimentDataRecorder** (`experiment_data_recorder.py`)
   - Centralized recording coordinator
   - LSL stream discovery and management
   - Session management and file organization
   - Event logging and synchronization

2. **Task LSL Publishers** (`task_lsl_publishers.py`)
   - M1TappingLSLPublisher: Motor task event streaming
   - V1OrientationLSLPublisher: Visual task event streaming
   - PhysiologicalDataPublisher: Biosignal streaming

3. **FSL-MRS LSL Publisher** (`fsl_mrs_lsl_publisher.py`)
   - E/I ratio data streaming
   - Realistic MRS data simulation
   - Intervention control

4. **Data Analysis Tools** (`data_analysis.py`)
   - Comprehensive post-experiment analysis
   - Statistical analysis and visualization
   - Report generation

### Data Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FSL-MRS       │    │   Task Events   │    │  Physiological  │
│   Publisher     │    │   Publishers    │    │   Publisher     │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │  Experiment Data Recorder │
                    │  (LSL Stream Manager)     │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │    Synchronized Files     │
                    │  • session_info.json     │
                    │  • events.csv/.json       │
                    │  • FSL-MRS-EI-Ratio.csv  │
                    │  • M1-Tapping-Task.csv    │
                    │  • V1-Orientation-Task.csv│
                    │  • Physiological-Data.csv │
                    └───────────────────────────┘
```

## Usage

### Starting a Recording Session

```python
from experiment_data_recorder import get_experiment_recorder

# Get the global recorder instance
recorder = get_experiment_recorder()

# Start a new session
session = recorder.start_session(
    participant_id="P001",
    session_id="session_001",
    experiment_name="realtime_mrs"
)

# Start recording all available LSL streams
recorder.start_recording()
```

### Logging Events

```python
from experiment_data_recorder import log_experiment_event

# Log task start
log_experiment_event('task_start', 'm1_tapping', {
    'trial_number': 1,
    'sequence': ['1', '2', '3', '4']
})

# Log stimulus presentation
log_experiment_event('stimulus', 'v1_orientation', {
    'orientation': 45.0,
    'duration': 0.1,
    'trial_number': 5
})

# Log response
log_experiment_event('response', 'm1_tapping', {
    'key_pressed': '2',
    'reaction_time': 0.234,
    'is_correct': True
})
```

### Task-Specific Publishers

#### M1 Tapping Task

```python
from task_lsl_publishers import get_m1_publisher

m1_pub = get_m1_publisher()

# Log trial events
m1_pub.trial_start(trial_number=1, sequence=['1', '2', '3', '4'])
m1_pub.sequence_start(trial_number=1, sequence=['1', '2', '3', '4'])
m1_pub.tap_event(
    trial_number=1,
    sequence_position=0,
    target_key='1',
    pressed_key='1',
    reaction_time=0.234,
    is_correct=True
)
m1_pub.sequence_end(trial_number=1)
m1_pub.trial_end(trial_number=1)
```

#### V1 Orientation Task

```python
from task_lsl_publishers import get_v1_publisher

v1_pub = get_v1_publisher()

# Log trial events
v1_pub.trial_start(trial_number=1)
v1_pub.stimulus_on(trial_number=1, orientation=45.0, duration=0.1)
v1_pub.stimulus_off(trial_number=1)
v1_pub.response_event(
    trial_number=1,
    response_key='left',
    reaction_time=0.456,
    is_correct=True
)
v1_pub.trial_end(trial_number=1)
```

### Ending a Session

```python
# Stop recording
recorder.stop_recording()

# End session (saves all data)
recorder.end_session()
```

## Data Organization

### Directory Structure

Each experiment session creates a timestamped directory:

```
experiment_data/
└── P001_session_001_20241201_143022/
    ├── session_info.json              # Session metadata
    ├── events.json                    # All events (detailed)
    ├── events.csv                     # All events (tabular)
    ├── FSL-MRS-EI-Ratio_20241201_143022.csv
    ├── M1-Tapping-Task_20241201_143022.csv
    ├── V1-Orientation-Task_20241201_143022.csv
    ├── Physiological-Data_20241201_143022.csv
    └── ExperimentEvents_20241201_143022.csv
```

### File Formats

#### Session Info (`session_info.json`)
```json
{
  "participant_id": "P001",
  "session_id": "session_001",
  "experiment_name": "realtime_mrs",
  "start_time": "2024-12-01T14:30:22.123456",
  "end_time": "2024-12-01T15:15:45.789012",
  "data_directory": "/path/to/data",
  "recording_files": {
    "FSL-MRS-EI-Ratio": "FSL-MRS-EI-Ratio_20241201_143022.csv",
    "M1-Tapping-Task": "M1-Tapping-Task_20241201_143022.csv"
  }
}
```

#### Events (`events.csv`)
```csv
timestamp,event_type,task_name,participant_id,session_id,event_data
1701434222.123,session_start,experiment,P001,session_001,"{""start_time"": ""2024-12-01T14:30:22""}"
1701434225.456,task_start,m1_tapping,P001,session_001,"{""trial_number"": 1}"
1701434226.789,tap,m1_tapping,P001,session_001,"{""reaction_time"": 0.234, ""is_correct"": true}"
```

#### Stream Data (`*_timestamp.csv`)
```csv
timestamp,data
1701434222.123,0.756
1701434223.123,0.742
1701434224.123,0.768
```

For task streams, data is JSON-encoded:
```csv
timestamp,data
1701434222.123,"{""event_type"": ""tap"", ""trial_number"": 1, ""reaction_time"": 0.234}"
```

## Data Analysis

### Running Analysis

```bash
# Analyze a specific session
python data_analysis.py experiment_data/P001_session_001_20241201_143022/

# Skip plot generation
python data_analysis.py experiment_data/P001_session_001_20241201_143022/ --no-plots

# Skip report generation
python data_analysis.py experiment_data/P001_session_001_20241201_143022/ --no-report
```

### Programmatic Analysis

```python
from data_analysis import ExperimentDataAnalyzer

# Create analyzer
analyzer = ExperimentDataAnalyzer('experiment_data/P001_session_001_20241201_143022/')

# Load data
analyzer.load_session_data()

# Run specific analyses
mrs_results = analyzer.analyze_mrs_data()
task_results = analyzer.analyze_task_performance()
correlation_results = analyzer.analyze_mrs_task_correlation()

# Generate visualizations
analyzer.generate_visualizations()

# Generate report
analyzer.generate_report()

# Or run everything
analyzer.run_complete_analysis()
```

### Analysis Outputs

The analysis generates:

1. **Statistical Reports** (`analysis_report.json`)
   - MRS data statistics (mean, std, trends)
   - Task performance metrics (accuracy, reaction times)
   - MRS-task correlations

2. **Visualizations** (`analysis_plots/`)
   - `mrs_timeseries.png`: E/I ratio over time
   - `mrs_distribution.png`: E/I ratio distribution
   - `m1_performance.png`: M1 task performance plots
   - `v1_performance.png`: V1 task performance plots
   - `correlations.png`: MRS-task correlation plots
   - `summary_dashboard.png`: Comprehensive overview

## Configuration

### Recording Configuration (`config.yaml`)

```yaml
experiment_recording:
  data_directory: 'experiment_data'
  auto_save_interval: 30.0  # seconds
  streams_to_record:
    - 'FSL-MRS-EI-Ratio'
    - 'ExperimentEvents'
    - 'M1-Tapping-Task'
    - 'V1-Orientation-Task'
    - 'Physiological-Data'
  file_formats: ['csv', 'json']
  buffer_length: 360  # seconds
  sync_tolerance: 0.001  # seconds

task_lsl_publishers:
  m1_tapping:
    stream_name: 'M1-Tapping-Task'
    stream_type: 'TaskData'
    source_id: 'm1-tapping-001'
  
  v1_orientation:
    stream_name: 'V1-Orientation-Task'
    stream_type: 'TaskData'
    source_id: 'v1-orientation-001'
  
  physiological:
    stream_name: 'Physiological-Data'
    stream_type: 'Physiological'
    source_id: 'physio-001'
    sampling_rate: 100.0  # Hz
    channels:
      - 'heart_rate'
      - 'eye_x'
      - 'eye_y'
      - 'pupil_diameter'
      - 'blink'
```

## Integration with Existing Tasks

### Updating Task Files

To integrate LSL recording with existing tasks, add publisher initialization and event logging:

```python
# At the top of task file
from task_lsl_publishers import get_m1_publisher
from experiment_data_recorder import log_experiment_event

# In task initialization
self.lsl_publisher = get_m1_publisher()

# In task methods
def start_trial(self, trial_number, sequence):
    # Existing code...
    
    # Add LSL logging
    self.lsl_publisher.trial_start(trial_number, sequence)
    log_experiment_event('trial_start', 'm1_tapping', {
        'trial_number': trial_number,
        'sequence': sequence
    })

def handle_key_press(self, key, trial_number, sequence_position, target_key):
    # Existing code...
    reaction_time = time.time() - self.stimulus_start_time
    is_correct = (key == target_key)
    
    # Add LSL logging
    self.lsl_publisher.tap_event(
        trial_number, sequence_position, target_key, 
        key, reaction_time, is_correct
    )
```

## Advanced Features

### Real-time Data Monitoring

```python
# Monitor recording status
status = recorder.get_session_status()
print(f"Recording: {status['is_recording']}")
print(f"Streams: {status['recorded_streams']}")
print(f"Events: {status['total_events']}")
```

### Custom Event Types

```python
# Log custom intervention events
log_experiment_event('intervention', 'fsl_mrs', {
    'intervention_type': 'excitatory',
    'magnitude': 0.3,
    'target_region': 'M1'
})

# Log physiological markers
log_experiment_event('physiological_marker', 'monitoring', {
    'marker_type': 'heart_rate_spike',
    'value': 95.2,
    'threshold': 90.0
})
```

### Stream Synchronization

All LSL streams are automatically synchronized using LSL's built-in clock synchronization. The system ensures:

- Sub-millisecond timing accuracy
- Automatic clock drift correction
- Cross-platform compatibility
- Network-transparent operation

## Troubleshooting

### Common Issues

1. **No LSL streams found**
   - Ensure LSL publishers are started before recording
   - Check network connectivity for remote streams
   - Verify stream names in configuration

2. **Missing data files**
   - Check that recording was started before data generation
   - Verify write permissions in data directory
   - Ensure sufficient disk space

3. **Analysis errors**
   - Verify data file integrity
   - Check for required Python packages (pandas, matplotlib, seaborn)
   - Ensure data directory structure is correct

### Debugging

Enable debug logging:

```python
import logging
logging.getLogger("ExperimentDataRecorder").setLevel(logging.DEBUG)
logging.getLogger("TaskLSLPublishers").setLevel(logging.DEBUG)
```

## Dependencies

### Required Packages

```bash
pip install pylsl pandas numpy matplotlib seaborn
```

### Optional Packages

```bash
pip install pyxdf  # For XDF file format support
pip install scipy  # For advanced statistical analysis
```

## Best Practices

1. **Session Management**
   - Always call `start_session()` before recording
   - Use descriptive participant and session IDs
   - Call `end_session()` to ensure data is saved

2. **Event Logging**
   - Log events immediately when they occur
   - Include relevant context in event data
   - Use consistent event type naming

3. **Data Organization**
   - Use standardized participant ID formats
   - Include session metadata in filenames
   - Backup data regularly

4. **Performance**
   - Monitor disk space during long sessions
   - Use appropriate auto-save intervals
   - Consider data compression for large datasets

## Future Enhancements

- **Real-time Analysis**: Live data processing and feedback
- **Cloud Storage**: Automatic backup to cloud services
- **Advanced Synchronization**: Multi-site data collection
- **Machine Learning**: Real-time pattern detection
- **Mobile Integration**: Smartphone-based data collection

This comprehensive data acquisition and recording system provides a robust foundation for multi-modal neuroscience experiments with precise timing and synchronization capabilities. 